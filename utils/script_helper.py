#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
脚本辅助工具 - 消除重复代码，提供通用功能

提供的功能：
1. 自动路径设置（项目根目录自动添加到sys.path）
2. 输出目录管理（自动创建results目录）
3. 文件命名规范（统一的输出文件命名）
4. 通用配置加载

作者: Claude
日期: 2025-10-23
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, Any
import json


class ScriptHelper:
    """脚本辅助类 - 提供通用的脚本设置和工具函数"""

    def __init__(self, script_file: str, auto_setup: bool = True):
        """
        初始化脚本助手

        Args:
            script_file: 脚本文件路径（通常传入__file__）
            auto_setup: 是否自动设置路径（默认True）

        用法:
            # 在脚本开头
            from utils.script_helper import ScriptHelper
            helper = ScriptHelper(__file__)
            # 现在project_root已自动添加到sys.path
        """
        self.script_path = Path(script_file).resolve()
        self.script_dir = self.script_path.parent
        self.script_name = self.script_path.stem

        # 自动查找项目根目录（包含solvers/和utils/的目录）
        self.project_root = self._find_project_root()

        if auto_setup:
            self.setup_paths()

    def _find_project_root(self) -> Path:
        """
        自动查找项目根目录

        查找策略：从当前目录向上查找，直到找到包含solvers/和utils/的目录

        Returns:
            项目根目录路径
        """
        current = self.script_dir
        max_depth = 10  # 最多向上查找10层

        for _ in range(max_depth):
            # 检查是否包含solvers/和utils/目录
            if (current / 'solvers').exists() and (current / 'utils').exists():
                return current

            # 向上一层
            parent = current.parent
            if parent == current:  # 已到根目录
                break
            current = parent

        # 如果没找到，返回脚本所在目录的上两层（默认猜测）
        return self.script_dir.parent.parent

    def setup_paths(self):
        """
        设置Python路径

        自动将项目根目录添加到sys.path，确保可以导入项目模块
        """
        project_root_str = str(self.project_root)
        if project_root_str not in sys.path:
            sys.path.insert(0, project_root_str)

    def get_output_dir(self, subdir: str = "results", create: bool = True) -> Path:
        """
        获取输出目录路径

        Args:
            subdir: 子目录名称（默认"results"）
            create: 是否自动创建目录（默认True）

        Returns:
            输出目录路径

        用法:
            output_dir = helper.get_output_dir()
            # 返回: script_dir/results/
        """
        output_dir = self.script_dir / subdir

        if create and not output_dir.exists():
            output_dir.mkdir(parents=True, exist_ok=True)

        return output_dir

    def get_output_path(self, filename: str, subdir: str = "results",
                       create_dir: bool = True) -> Path:
        """
        获取输出文件的完整路径

        Args:
            filename: 文件名
            subdir: 子目录名称（默认"results"）
            create_dir: 是否自动创建目录（默认True）

        Returns:
            完整文件路径

        用法:
            fig_path = helper.get_output_path("figure.png")
            plt.savefig(fig_path)
        """
        output_dir = self.get_output_dir(subdir, create=create_dir)
        return output_dir / filename

    def save_config(self, config: Dict[str, Any], filename: str = "config.json"):
        """
        保存配置到JSON文件

        Args:
            config: 配置字典
            filename: 文件名（默认"config.json"）
        """
        config_path = self.get_output_path(filename)
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def load_config(self, filename: str = "config.json") -> Optional[Dict[str, Any]]:
        """
        从JSON文件加载配置

        Args:
            filename: 文件名（默认"config.json"）

        Returns:
            配置字典，如果文件不存在则返回None
        """
        config_path = self.get_output_dir() / filename
        if not config_path.exists():
            return None

        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def __repr__(self) -> str:
        return (f"ScriptHelper(\n"
                f"  script_path={self.script_path},\n"
                f"  project_root={self.project_root}\n"
                f")")


# 便捷函数：快速设置路径
def quick_setup(script_file: str) -> ScriptHelper:
    """
    快速设置脚本环境

    这是最简单的使用方式，一行代码完成所有设置

    Args:
        script_file: 脚本文件路径（传入__file__）

    Returns:
        ScriptHelper实例

    用法:
        from utils.script_helper import quick_setup
        helper = quick_setup(__file__)
        # 路径已设置，可以直接导入项目模块
        from solvers.hydrostatic_canal_solver import HydrostaticCanalSolver
    """
    return ScriptHelper(script_file, auto_setup=True)


# 向后兼容的函数
def setup_project_path(script_file: str) -> tuple:
    """
    设置项目路径（向后兼容函数）

    Args:
        script_file: 脚本文件路径（传入__file__）

    Returns:
        (script_path, project_root, script_dir)元组
    """
    helper = ScriptHelper(script_file, auto_setup=True)
    return str(helper.script_path), str(helper.project_root), str(helper.script_dir)


if __name__ == "__main__":
    """测试脚本助手"""
    print("=" * 80)
    print("ScriptHelper测试")
    print("=" * 80)
    print()

    # 创建助手
    helper = ScriptHelper(__file__)

    print("脚本信息:")
    print(f"  脚本路径: {helper.script_path}")
    print(f"  脚本目录: {helper.script_dir}")
    print(f"  脚本名称: {helper.script_name}")
    print(f"  项目根目录: {helper.project_root}")
    print()

    print("测试输出目录:")
    output_dir = helper.get_output_dir()
    print(f"  默认输出目录: {output_dir}")
    print(f"  目录存在: {output_dir.exists()}")
    print()

    print("测试输出文件路径:")
    fig_path = helper.get_output_path("test_figure.png")
    data_path = helper.get_output_path("test_data.npz")
    print(f"  图片路径: {fig_path}")
    print(f"  数据路径: {data_path}")
    print()

    print("测试配置管理:")
    test_config = {
        "parameter1": 10.0,
        "parameter2": "test_value",
        "nested": {
            "sub1": 1,
            "sub2": 2
        }
    }
    helper.save_config(test_config, "test_config.json")
    loaded_config = helper.load_config("test_config.json")
    print(f"  保存的配置: {test_config}")
    print(f"  加载的配置: {loaded_config}")
    print(f"  配置匹配: {test_config == loaded_config}")
    print()

    print("测试便捷函数:")
    helper2 = quick_setup(__file__)
    print(f"  {helper2}")
    print()

    print("✓ ScriptHelper测试完成！")
    print("=" * 80)
