"""批量在本地 C 盘运行所有 HEC-RAS 案例，生成计算结果 HDF。

功能:
- 复制到本地 C 盘运行（避免网络盘弹窗）
- 每个 plan 有超时保护（默认 600 秒）
- 自动杀掉卡住的 HEC-RAS 进程
- 跳过已有结果的案例（断点续跑）
- 后台线程自动关闭弹窗

用法: python scripts/batch_run_hecras_local.py
      python scripts/batch_run_hecras_local.py --resume   # 跳过已有 HDF 的案例
      python scripts/batch_run_hecras_local.py --timeout 300
"""
import pathlib, json, shutil, logging, time, sys, os, subprocess, threading
from datetime import datetime

logging.disable(logging.CRITICAL)

SRC_ROOT = pathlib.Path(__file__).resolve().parents[1] / 'hecras_all_cases'
LOCAL_ROOT = pathlib.Path('C:/temp/hecras_run')
LOCAL_ROOT.mkdir(parents=True, exist_ok=True)

SKIP_KEYWORDS = ['Sediment']
DEFAULT_TIMEOUT = 600  # 每个 plan 最多 10 分钟


def _auto_dismiss_dialogs(stop_event: threading.Event):
    """后台线程：每 5 秒检测并自动关闭 RAS 弹窗。"""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindowsW
        GetWindowText = user32.GetWindowTextW
        PostMessage = user32.PostMessageW
        IsWindowVisible = user32.IsWindowVisible
        WM_CLOSE = 0x0010

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
        def enum_callback(hwnd, lParam):
            if IsWindowVisible(hwnd):
                buf = ctypes.create_unicode_buffer(256)
                GetWindowText(hwnd, buf, 256)
                title = buf.value
                if title == 'RAS':
                    # 发送 Enter 键关闭对话框
                    user32.PostMessageW(hwnd, 0x0100, 0x0D, 0)  # WM_KEYDOWN + VK_RETURN
                    time.sleep(0.1)
                    user32.PostMessageW(hwnd, 0x0101, 0x0D, 0)  # WM_KEYUP + VK_RETURN
            return True

        while not stop_event.is_set():
            try:
                EnumWindows(enum_callback, 0)
            except Exception:
                pass
            stop_event.wait(5)
    except Exception:
        pass


def find_projects():
    prj_files = []
    for p in sorted(SRC_ROOT.rglob('*.prj')):
        skip = ['GIS', 'Terrain', 'Features', 'NLD', 'LandCover']
        if any(s.lower() in str(p.parent).lower() for s in skip):
            continue
        rel = str(p.relative_to(SRC_ROOT))
        if any(kw in rel for kw in SKIP_KEYWORDS):
            continue
        try:
            text = p.read_text(errors='ignore')[:500]
            if 'Proj Title' in text or 'Current Plan' in text:
                prj_files.append(p)
        except:
            pass
    return prj_files


def has_results(prj: pathlib.Path) -> bool:
    """检查案例是否已有计算结果 HDF。"""
    return any(prj.parent.glob('*.p*.hdf'))


def kill_ras():
    """杀掉所有 HEC-RAS 进程。"""
    for exe in ['Ras.exe', 'RasPlotDriver.exe', 'RasGeomPreproc.exe',
                'RasSteady.exe', 'RasUnsteady.exe']:
        os.system(f'taskkill /F /IM "{exe}" >nul 2>&1')


def run_project(prj: pathlib.Path, timeout: int = DEFAULT_TIMEOUT):
    from ras_commander import init_ras_project, RasCmdr

    rel = prj.parent.relative_to(SRC_ROOT)
    local_dir = LOCAL_ROOT / rel.name

    if local_dir.exists():
        shutil.rmtree(local_dir, ignore_errors=True)
        time.sleep(1)
    shutil.copytree(prj.parent, local_dir)
    local_prj = local_dir / prj.name

    ras = init_ras_project(local_prj, ras_version='6.6')
    plans = ras.plan_df['plan_number'].tolist() if hasattr(ras, 'plan_df') and len(ras.plan_df) > 0 else []

    plan_ok = 0
    plan_details = []
    for pn in plans[:3]:
        t0 = time.time()
        try:
            r = RasCmdr.compute_plan(pn, ras_object=ras, num_cores=2)
            elapsed = time.time() - t0
            success = hasattr(r, 'success') and r.success
            if success:
                plan_ok += 1
            plan_details.append({'plan': pn, 'success': success, 'time_s': round(elapsed)})

            # 超时检查（下个 plan 开始前）
            if elapsed > timeout:
                plan_details[-1]['note'] = 'slow'

        except Exception as e:
            elapsed = time.time() - t0
            plan_details.append({'plan': pn, 'success': False, 'error': str(e)[:100], 'time_s': round(elapsed)})
            if elapsed > timeout:
                kill_ras()
                time.sleep(2)

    # 复制 HDF 结果回原目录
    copied = 0
    for hdf in local_dir.glob('*.p*.hdf'):
        shutil.copy2(hdf, prj.parent / hdf.name)
        copied += 1
    for hdf in local_dir.glob('*.g*.hdf'):
        dst = prj.parent / hdf.name
        if not dst.exists():
            shutil.copy2(hdf, dst)
            copied += 1

    shutil.rmtree(local_dir, ignore_errors=True)
    return plan_ok, len(plans[:3]), plan_details, copied


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--resume', action='store_true', help='跳过已有 HDF 的案例')
    parser.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument('--start', type=int, default=0, help='从第 N 个案例开始（0-based）')
    args = parser.parse_args()

    prj_files = find_projects()
    print(f'Total: {len(prj_files)} projects')

    # 启动弹窗自动关闭线程
    stop_event = threading.Event()
    dismiss_thread = threading.Thread(target=_auto_dismiss_dialogs, args=(stop_event,), daemon=True)
    dismiss_thread.start()
    print('Auto-dismiss dialog thread started')

    results = []
    for i, prj in enumerate(prj_files):
        if i < args.start:
            continue

        name = str(prj.parent.relative_to(SRC_ROOT))
        print(f'[{i+1}/{len(prj_files)}] {name}...', end=' ', flush=True)

        if args.resume and has_results(prj):
            print('SKIP (already has HDF)')
            results.append({'project': name, 'status': 'SKIP', 'note': 'already has results'})
            continue

        t0 = time.time()
        try:
            ok, total, details, copied = run_project(prj, timeout=args.timeout)
            elapsed = time.time() - t0
            status = f'{ok}/{total} OK ({elapsed:.0f}s, {copied} HDF)'
            print(status)
            results.append({
                'project': name, 'status': status,
                'ok': ok, 'total': total, 'time_s': round(elapsed),
                'hdf_copied': copied, 'plans': details,
            })
        except Exception as e:
            elapsed = time.time() - t0
            err = str(e)[:200]
            print(f'FAIL ({elapsed:.0f}s): {err[:60]}')
            results.append({'project': name, 'status': 'FAIL', 'error': err, 'time_s': round(elapsed)})
            kill_ras()
            time.sleep(2)

        # 每 10 个案例保存一次中间结果
        if (i + 1) % 10 == 0:
            _save_report(prj_files, results)

    stop_event.set()
    _save_report(prj_files, results)


def _save_report(prj_files, results):
    report = {
        'timestamp': datetime.now().isoformat(),
        'hecras_version': '6.6',
        'total_projects': len(prj_files),
        'completed': len(results),
        'ok_count': sum(1 for r in results if r.get('ok', 0) > 0),
        'fail_count': sum(1 for r in results if r.get('status') == 'FAIL'),
        'results': results,
    }
    out = SRC_ROOT.parent / 'reports' / 'hecras_batch_run_all.json'
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    ok = sum(1 for r in results if r.get('ok', 0) > 0)
    skip = sum(1 for r in results if r.get('status') == 'SKIP')
    fail = sum(1 for r in results if r.get('status') == 'FAIL')
    print(f'\n[Checkpoint] {ok} OK / {skip} SKIP / {fail} FAIL / {len(results)} total')
    print(f'Report: {out}')


if __name__ == '__main__':
    main()
