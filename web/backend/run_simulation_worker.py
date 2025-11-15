#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仿真任务Worker脚本
用于在独立进程中运行仿真任务，解决FastAPI BackgroundTasks的模块导入问题

使用方法:
    python run_simulation_worker.py --task-id <task_id> --config <config_json>

Author: HydroClaude
Date: 2025-11-15
"""

import sys
import os
import json
import argparse
from datetime import datetime

# ========== 设置路径（必须在导入前）==========
backend_path = os.path.dirname(os.path.abspath(__file__))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

# ========== 导入核心模块 ==========
try:
    from core.hydraulic_engine import HydraulicEngine
except ImportError as e:
    print(f"❌ 导入失败: {e}", file=sys.stderr)
    print(f"sys.path: {sys.path}", file=sys.stderr)
    sys.exit(1)

# ========== 输出抑制上下文管理器 ==========
import contextlib
import io

@contextlib.contextmanager
def suppress_output():
    """抑制stdout和stderr输出"""
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    try:
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()
        yield
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr


def run_simulation(task_id: str, config: dict) -> dict:
    """
    运行仿真任务
    
    Args:
        task_id: 任务ID
        config: 仿真配置
        
    Returns:
        仿真结果字典
    """
    result = {
        "task_id": task_id,
        "status": "running",
        "started_at": datetime.now().isoformat(),
        "config": config
    }
    
    try:
        # 创建引擎实例
        engine = HydraulicEngine()
        
        # 提取必要参数
        name = config.get("name", "unnamed_simulation")
        
        # 运行仿真（抑制输出）
        with suppress_output():
            simulation_result = engine.run_canal_simulation(name, config)
        
        # 将SimulationResult对象转换为字典
        if hasattr(simulation_result, 'model_dump'):
            # Pydantic v2
            result_dict = simulation_result.model_dump()
        elif hasattr(simulation_result, 'dict'):
            # Pydantic v1
            result_dict = simulation_result.dict()
        else:
            # 普通对象，使用vars()
            result_dict = vars(simulation_result) if hasattr(simulation_result, '__dict__') else str(simulation_result)
        
        # 构造响应
        result.update({
            "status": "completed",
            "completed_at": datetime.now().isoformat(),
            "result": result_dict
        })
        
    except Exception as e:
        result.update({
            "status": "failed",
            "completed_at": datetime.now().isoformat(),
            "error": str(e)
        })
    
    return result


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="运行仿真任务")
    parser.add_argument("--task-id", required=True, help="任务ID")
    parser.add_argument("--config", required=True, help="仿真配置（JSON字符串）")
    parser.add_argument("--output", help="输出文件路径（可选）")
    
    args = parser.parse_args()
    
    # 解析配置
    try:
        config = json.loads(args.config)
    except json.JSONDecodeError as e:
        print(f"❌ 配置JSON解析失败: {e}", file=sys.stderr)
        sys.exit(1)
    
    # 运行仿真
    result = run_simulation(args.task_id, config)
    
    # 输出结果
    result_json = json.dumps(result, ensure_ascii=False, indent=2)
    
    if args.output:
        # 保存到文件
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(result_json)
    else:
        # 输出到stdout
        print(result_json)
    
    # 返回状态码
    if result["status"] == "completed":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
