#!/usr/bin/env python3
"""HEC-RAS 批量运行器 — 生产级。

通过读取 HDF 结果文件判断计算进度和成功/失败，不使用固定 timeout。
自动处理 plan 依赖顺序，记录所有错误和警告。

用法:
    python scripts/hecras_runner.py                          # 运行全部案例
    python scripts/hecras_runner.py --resume                 # 跳过已有结果的案例
    python scripts/hecras_runner.py --category "1D Steady"   # 只跑某类别
    python scripts/hecras_runner.py --case "Example 1"       # 只跑某案例
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import h5py

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('hecras_runner')

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
CASES_ROOT = PROJECT_ROOT / 'hecras_all_cases'
LOCAL_WORK = pathlib.Path('C:/temp/hecras_run')
REPORT_DIR = PROJECT_ROOT / 'reports'

SKIP_CATEGORIES = ['Sediment']  # 泥沙模型暂不支持

# HEC-RAS 进程名
RAS_PROCESSES = ['Ras.exe', 'RasPlotDriver.exe', 'RasGeomPreproc.exe',
                 'RasSteady.exe', 'RasUnsteady.exe', 'RasProcess.exe']

# HDF 里判断完成的关键词
FINISHED_KEYWORDS = [
    'Finished Steady Flow Simulation',
    'Finished Unsteady Flow Simulation',
    'Finished Post Processing',
    'Complete Process',
]
ERROR_KEYWORDS = [
    'ERROR', 'Error', 'FATAL', 'Fatal',
    'Encroachment', 'base plan results file is not available',
    'not converging', 'Aborting',
]
WARNING_KEYWORDS = [
    'WARNING', 'Warning', 'discontinued',
]


@dataclass
class PlanResult:
    plan_number: str
    success: bool = False
    finished: bool = False
    compute_time_s: float = 0.0
    messages: str = ''
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    hdf_path: str | None = None


@dataclass
class CaseResult:
    project: str
    category: str
    prj_path: str
    plans: list[PlanResult] = field(default_factory=list)
    ok_count: int = 0
    total_plans: int = 0
    total_time_s: float = 0.0
    hdf_copied: int = 0
    status: str = 'PENDING'
    error: str | None = None


def find_projects(cases_root: pathlib.Path, category_filter: str | None = None,
                  case_filter: str | None = None) -> list[pathlib.Path]:
    """查找所有有效的 HEC-RAS 项目文件。"""
    prj_files = []
    skip_dirs = {'gis', 'gisdata', 'gis_data', 'terrain', 'features', 'nld', 'landcover'}

    for p in sorted(cases_root.rglob('*.prj')):
        # 跳过 GIS projection 文件
        if any(sd in str(p.parent).lower() for sd in skip_dirs):
            continue

        rel = str(p.relative_to(cases_root))

        # 跳过不支持的类别
        if any(kw in rel for kw in SKIP_CATEGORIES):
            continue

        # 类别过滤
        if category_filter and category_filter.lower() not in rel.lower():
            continue

        # 案例名过滤
        if case_filter and case_filter.lower() not in rel.lower():
            continue

        # 验证是 HEC-RAS 项目文件
        try:
            text = p.read_text(errors='ignore')[:500]
            if 'Proj Title' in text or 'Current Plan' in text:
                prj_files.append(p)
        except OSError:
            pass

    return prj_files


def parse_plan_order(prj_path: pathlib.Path) -> list[str]:
    """从 .prj 文件解析 plan 顺序。

    HEC-RAS .prj 文件中 Plan File 按声明顺序列出，
    通常 base plan 在前，依赖 plan 在后。
    """
    plans = []
    try:
        for line in prj_path.read_text(errors='ignore').splitlines():
            line = line.strip()
            if line.startswith('Plan File='):
                pn = line.split('=', 1)[1].strip()
                # pn 格式如 "p01" → 取 "01"
                if pn.lower().startswith('p'):
                    plans.append(pn[1:])
                else:
                    plans.append(pn)
    except OSError:
        pass
    return plans


def read_hdf_messages(hdf_path: pathlib.Path) -> dict[str, Any]:
    """从 HDF 结果文件读取计算信息。"""
    result = {
        'exists': False,
        'finished': False,
        'messages': '',
        'errors': [],
        'warnings': [],
        'compute_time': {},
    }

    if not hdf_path.exists():
        return result

    result['exists'] = True

    try:
        with h5py.File(str(hdf_path), 'r') as f:
            # 读取 Compute Messages
            for msg_path in ['Results/Summary/Compute Messages (text)',
                             'Results/Summary/Compute Messages']:
                ds = f.get(msg_path)
                if ds is not None:
                    raw = ds[()]
                    if isinstance(raw, (list, tuple)):
                        raw = raw[0] if raw else b''
                    if isinstance(raw, bytes):
                        raw = raw.decode('utf-8', errors='replace')
                    elif isinstance(raw, str):
                        pass
                    else:
                        raw = str(raw)
                    result['messages'] = raw
                    break

            # 判断是否完成
            msg = result['messages']
            result['finished'] = any(kw in msg for kw in FINISHED_KEYWORDS)

            # 提取错误
            for line in msg.split('\n'):
                line = line.strip()
                if any(kw in line for kw in ERROR_KEYWORDS):
                    result['errors'].append(line)
                if any(kw in line for kw in WARNING_KEYWORDS):
                    result['warnings'].append(line)

            # 提取计算时间
            for line in msg.split('\n'):
                if '\t' in line and any(c.isdigit() for c in line):
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        task = parts[0].strip()
                        time_str = parts[-1].strip()
                        if task and time_str:
                            result['compute_time'][task] = time_str

    except Exception as e:
        result['errors'].append(f'HDF read error: {e}')

    return result


def poll_hdf_until_done(hdf_path: pathlib.Path, poll_interval: float = 5.0,
                        max_stall_s: float = 300.0) -> dict[str, Any]:
    """轮询 HDF 文件直到计算完成或卡住。

    不用固定 timeout，而是检测文件大小是否还在增长。
    如果文件大小连续 max_stall_s 秒没变化，认为卡住了。
    """
    last_size = 0
    last_change_time = time.time()
    hdf_existed = False

    while True:
        time.sleep(poll_interval)

        if not hdf_path.exists():
            # HDF 还没创建，可能还在预处理
            if time.time() - last_change_time > max_stall_s:
                return {'finished': False, 'stalled': True,
                        'reason': f'HDF not created after {max_stall_s}s'}
            continue

        if not hdf_existed:
            hdf_existed = True
            last_change_time = time.time()

        try:
            current_size = hdf_path.stat().st_size
        except OSError:
            continue

        if current_size != last_size:
            last_size = current_size
            last_change_time = time.time()

        # 尝试读取完成状态
        info = read_hdf_messages(hdf_path)
        if info['finished']:
            return info

        # 检查是否有致命错误
        if info['errors']:
            fatal = [e for e in info['errors'] if 'FATAL' in e or 'Aborting' in e]
            if fatal:
                return {**info, 'stalled': False}

        # 检查是否卡住
        stall_duration = time.time() - last_change_time
        if stall_duration > max_stall_s:
            return {**info, 'stalled': True,
                    'reason': f'HDF unchanged for {stall_duration:.0f}s'}


def kill_ras_processes():
    """杀掉所有 HEC-RAS 进程。"""
    for exe in RAS_PROCESSES:
        os.system(f'taskkill /F /IM "{exe}" >nul 2>&1')
    time.sleep(2)


def run_single_plan(local_prj: pathlib.Path, plan_number: str,
                    ras_object: Any) -> PlanResult:
    """运行单个 plan 并通过 HDF 监控进度。"""
    from ras_commander import RasCmdr

    result = PlanResult(plan_number=plan_number)
    t0 = time.time()

    # 预测 HDF 结果文件路径
    prj_stem = local_prj.stem
    hdf_name = f'{prj_stem}.p{plan_number}.hdf'
    hdf_path = local_prj.parent / hdf_name

    # 删除旧的 HDF（确保检测到新结果）
    if hdf_path.exists():
        try:
            hdf_path.unlink()
        except OSError:
            pass

    # 在后台线程启动 HEC-RAS
    compute_result = [None]
    compute_error = [None]

    def _run():
        try:
            compute_result[0] = RasCmdr.compute_plan(
                plan_number, ras_object=ras_object, num_cores=2)
        except Exception as e:
            compute_error[0] = str(e)

    run_thread = threading.Thread(target=_run, daemon=True)
    run_thread.start()

    # 主线程轮询 HDF 文件
    poll_info = poll_hdf_until_done(hdf_path, poll_interval=5.0, max_stall_s=300.0)

    # 等线程结束（最多再等 30 秒）
    run_thread.join(timeout=30.0)

    result.compute_time_s = time.time() - t0

    if poll_info.get('finished'):
        result.success = True
        result.finished = True
        result.messages = poll_info.get('messages', '')
        result.errors = poll_info.get('errors', [])
        result.warnings = poll_info.get('warnings', [])
        result.hdf_path = str(hdf_path) if hdf_path.exists() else None
    elif poll_info.get('stalled'):
        result.errors.append(f"STALLED: {poll_info.get('reason', 'unknown')}")
        kill_ras_processes()
    else:
        if compute_error[0]:
            result.errors.append(compute_error[0])
        result.errors.extend(poll_info.get('errors', []))
        result.warnings.extend(poll_info.get('warnings', []))
        result.messages = poll_info.get('messages', '')

    # 检查 ras_commander 返回值
    if compute_result[0] and hasattr(compute_result[0], 'success'):
        if compute_result[0].success and not result.success:
            # HDF 没检测到完成但 ras_commander 说成功
            result.success = True

    return result


def run_case(prj: pathlib.Path, cases_root: pathlib.Path,
             resume: bool = False) -> CaseResult:
    """运行一个完整的 HEC-RAS 案例（所有 plan）。"""
    from ras_commander import init_ras_project

    rel = prj.parent.relative_to(cases_root)
    category = str(rel).split('\\')[0] if '\\' in str(rel) else str(rel).split('/')[0]
    name = str(rel)

    case = CaseResult(project=name, category=category, prj_path=str(prj))

    # 检查是否已有结果
    if resume and any(prj.parent.glob('*.p*.hdf')):
        existing = list(prj.parent.glob('*.p*.hdf'))
        case.status = 'SKIP'
        case.hdf_copied = len(existing)
        log.info(f'SKIP {name} (already has {len(existing)} HDF)')
        return case

    t0 = time.time()

    # 复制到本地 C 盘
    local_dir = LOCAL_WORK / rel.name
    try:
        if local_dir.exists():
            shutil.rmtree(local_dir, ignore_errors=True)
            time.sleep(1)
        shutil.copytree(prj.parent, local_dir)
    except Exception as e:
        case.status = 'FAIL'
        case.error = f'Copy failed: {e}'
        log.error(f'FAIL {name}: {case.error}')
        return case

    local_prj = local_dir / prj.name

    # 初始化项目
    try:
        logging.disable(logging.CRITICAL)
        ras = init_ras_project(local_prj, ras_version='6.6')
        logging.disable(logging.NOTSET)
    except Exception as e:
        case.status = 'FAIL'
        case.error = f'Init failed: {e}'
        log.error(f'FAIL {name}: {case.error}')
        shutil.rmtree(local_dir, ignore_errors=True)
        return case

    # 获取 plan 顺序
    plan_order = parse_plan_order(local_prj)
    if not plan_order:
        # 从 ras_commander 获取
        try:
            plan_order = ras.plan_df['plan_number'].tolist()
        except Exception:
            plan_order = []

    case.total_plans = len(plan_order)

    # 按顺序执行每个 plan
    for pn in plan_order:
        log.info(f'  Plan {pn}...')
        pr = run_single_plan(local_prj, pn, ras)
        case.plans.append(pr)
        if pr.success:
            case.ok_count += 1
            log.info(f'  Plan {pn}: OK ({pr.compute_time_s:.0f}s)')
        else:
            errors_str = '; '.join(pr.errors[:3]) if pr.errors else 'unknown'
            log.warning(f'  Plan {pn}: FAIL ({pr.compute_time_s:.0f}s) - {errors_str[:100]}')

    # 复制 HDF 结果回原目录
    copied = 0
    for hdf in local_dir.glob('*.p*.hdf'):
        try:
            shutil.copy2(hdf, prj.parent / hdf.name)
            copied += 1
        except OSError:
            pass
    for hdf in local_dir.glob('*.g*.hdf'):
        dst = prj.parent / hdf.name
        if not dst.exists():
            try:
                shutil.copy2(hdf, dst)
                copied += 1
            except OSError:
                pass

    case.hdf_copied = copied
    case.total_time_s = time.time() - t0

    if case.ok_count == case.total_plans and case.total_plans > 0:
        case.status = 'OK'
    elif case.ok_count > 0:
        case.status = 'PARTIAL'
    else:
        case.status = 'FAIL'

    # 清理
    shutil.rmtree(local_dir, ignore_errors=True)

    log.info(f'{case.status} {name}: {case.ok_count}/{case.total_plans} plans, '
             f'{copied} HDF, {case.total_time_s:.0f}s')
    return case


def save_report(cases: list[CaseResult], output: pathlib.Path):
    """保存 JSON 报告。"""
    ok = sum(1 for c in cases if c.status == 'OK')
    partial = sum(1 for c in cases if c.status == 'PARTIAL')
    fail = sum(1 for c in cases if c.status == 'FAIL')
    skip = sum(1 for c in cases if c.status == 'SKIP')

    report = {
        'timestamp': datetime.now().isoformat(),
        'hecras_version': '6.6',
        'summary': {
            'total': len(cases),
            'ok': ok,
            'partial': partial,
            'fail': fail,
            'skip': skip,
        },
        'cases': [asdict(c) for c in cases],
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str))
    log.info(f'Report saved: {output}')
    log.info(f'Summary: {ok} OK / {partial} PARTIAL / {fail} FAIL / {skip} SKIP')


def main():
    parser = argparse.ArgumentParser(description='HEC-RAS 批量运行器')
    parser.add_argument('--resume', action='store_true', help='跳过已有 HDF 的案例')
    parser.add_argument('--category', help='只跑某类别 (如 "1D Steady")')
    parser.add_argument('--case', help='只跑某案例 (如 "Example 1")')
    parser.add_argument('--cases-root', default=str(CASES_ROOT))
    parser.add_argument('--output', default=str(REPORT_DIR / 'hecras_batch_run_all.json'))
    parser.add_argument('--start', type=int, default=0, help='从第 N 个案例开始（0-based）')
    args = parser.parse_args()

    cases_root = pathlib.Path(args.cases_root)
    if not cases_root.exists():
        log.error(f'Cases root not found: {cases_root}')
        sys.exit(1)

    LOCAL_WORK.mkdir(parents=True, exist_ok=True)

    prj_files = find_projects(cases_root, args.category, args.case)
    log.info(f'Found {len(prj_files)} projects')

    results: list[CaseResult] = []

    for i, prj in enumerate(prj_files):
        if i < args.start:
            continue

        rel = prj.parent.relative_to(cases_root)
        log.info(f'[{i+1}/{len(prj_files)}] {rel}')

        case = run_case(prj, cases_root, resume=args.resume)
        results.append(case)

        # 每 10 个案例保存中间结果
        if (i + 1) % 10 == 0 or i == len(prj_files) - 1:
            save_report(results, pathlib.Path(args.output))

    save_report(results, pathlib.Path(args.output))
    log.info('All done.')


if __name__ == '__main__':
    main()
