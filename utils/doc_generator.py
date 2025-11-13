#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
API文档生成器

自动扫描项目代码并生成API参考文档

功能：
1. 扫描Python模块
2. 提取类和函数的文档字符串
3. 生成Markdown格式的API文档
4. 创建索引和导航结构

作者: Claude
日期: 2025-10-24
"""

import os
import sys
import inspect
import importlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class FunctionDoc:
    """函数文档"""
    name: str
    signature: str
    docstring: str
    module: str
    is_method: bool = False
    is_static: bool = False
    is_classmethod: bool = False


@dataclass
class ClassDoc:
    """类文档"""
    name: str
    docstring: str
    module: str
    methods: List[FunctionDoc]
    attributes: List[str]
    bases: List[str]


@dataclass
class ModuleDoc:
    """模块文档"""
    name: str
    path: str
    docstring: str
    classes: List[ClassDoc]
    functions: List[FunctionDoc]
    submodules: List[str]


class APIDocGenerator:
    """
    API文档生成器

    用法：
    ```python
    generator = APIDocGenerator('/path/to/project')
    generator.scan_modules()
    generator.generate_markdown('api_docs')
    ```
    """

    def __init__(self, project_root: str, exclude_patterns: Optional[List[str]] = None):
        """
        初始化文档生成器

        Args:
            project_root: 项目根目录
            exclude_patterns: 排除的模式列表
        """
        self.project_root = Path(project_root)
        self.exclude_patterns = exclude_patterns or [
            '__pycache__',
            '.git',
            'venv',
            'env',
            '.pytest_cache',
            'build',
            'dist',
            '*.pyc',
            '*.pyo'
        ]
        self.modules: Dict[str, ModuleDoc] = {}

    def should_exclude(self, path: Path) -> bool:
        """检查路径是否应该排除"""
        path_str = str(path)
        for pattern in self.exclude_patterns:
            if pattern in path_str or path.name == pattern:
                return True
        return False

    def find_python_modules(self) -> List[Path]:
        """查找所有Python模块文件"""
        python_files = []
        for py_file in self.project_root.rglob('*.py'):
            if not self.should_exclude(py_file):
                python_files.append(py_file)
        return python_files

    def get_module_name(self, file_path: Path) -> str:
        """从文件路径获取模块名"""
        rel_path = file_path.relative_to(self.project_root)
        module_parts = list(rel_path.parts[:-1]) + [rel_path.stem]
        # 移除 __init__
        if module_parts[-1] == '__init__':
            module_parts = module_parts[:-1]
        return '.'.join(module_parts) if module_parts else ''

    def extract_function_doc(self, func: Any, module_name: str) -> FunctionDoc:
        """提取函数文档"""
        try:
            signature = str(inspect.signature(func))
        except (ValueError, TypeError):
            signature = '(...)'

        docstring = inspect.getdoc(func) or "无文档"

        return FunctionDoc(
            name=func.__name__,
            signature=signature,
            docstring=docstring,
            module=module_name,
            is_method=False,
            is_static=isinstance(inspect.getattr_static(func, '__func__', None),
                               staticmethod),
            is_classmethod=isinstance(inspect.getattr_static(func, '__func__', None),
                                     classmethod)
        )

    def extract_class_doc(self, cls: type, module_name: str) -> ClassDoc:
        """提取类文档"""
        docstring = inspect.getdoc(cls) or "无文档"

        # 提取方法
        methods = []
        for name, member in inspect.getmembers(cls):
            if name.startswith('_') and not name.startswith('__'):
                continue  # 跳过私有方法（但保留魔术方法）
            if inspect.isfunction(member) or inspect.ismethod(member):
                method_doc = self.extract_function_doc(member, module_name)
                method_doc.is_method = True
                methods.append(method_doc)

        # 提取类属性
        attributes = []
        for name, value in inspect.getmembers(cls):
            if not name.startswith('_') and not callable(value):
                attributes.append(name)

        # 基类
        bases = [base.__name__ for base in cls.__bases__ if base != object]

        return ClassDoc(
            name=cls.__name__,
            docstring=docstring,
            module=module_name,
            methods=methods,
            attributes=attributes,
            bases=bases
        )

    def extract_module_doc(self, module_path: Path) -> Optional[ModuleDoc]:
        """提取模块文档"""
        module_name = self.get_module_name(module_path)
        if not module_name:
            return None

        try:
            # 添加项目根目录到sys.path
            if str(self.project_root) not in sys.path:
                sys.path.insert(0, str(self.project_root))

            # 导入模块
            module = importlib.import_module(module_name)

            docstring = inspect.getdoc(module) or ""

            # 提取类
            classes = []
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # 只包含在当前模块定义的类
                if obj.__module__ == module_name:
                    class_doc = self.extract_class_doc(obj, module_name)
                    classes.append(class_doc)

            # 提取函数
            functions = []
            for name, obj in inspect.getmembers(module, inspect.isfunction):
                # 只包含在当前模块定义的函数
                if obj.__module__ == module_name:
                    func_doc = self.extract_function_doc(obj, module_name)
                    functions.append(func_doc)

            # 子模块（简化处理）
            submodules = []

            return ModuleDoc(
                name=module_name,
                path=str(module_path.relative_to(self.project_root)),
                docstring=docstring,
                classes=classes,
                functions=functions,
                submodules=submodules
            )

        except Exception as e:
            print(f"警告: 无法导入模块 {module_name}: {e}")
            return None

    def scan_modules(self):
        """扫描所有模块"""
        print("扫描Python模块...")
        python_files = self.find_python_modules()
        print(f"找到 {len(python_files)} 个Python文件")

        for py_file in python_files:
            module_doc = self.extract_module_doc(py_file)
            if module_doc:
                self.modules[module_doc.name] = module_doc
                print(f"   {module_doc.name}")

        print(f"\n成功扫描 {len(self.modules)} 个模块")

    def format_docstring(self, docstring: str, indent: int = 0) -> str:
        """格式化文档字符串为Markdown"""
        if not docstring:
            return ""

        lines = docstring.split('\n')
        formatted = []
        indent_str = ' ' * indent

        in_code_block = False
        for line in lines:
            stripped = line.strip()

            # 检测代码块
            if stripped.startswith('```') or stripped.startswith('>>>'):
                in_code_block = not in_code_block

            # 检测参数列表
            if stripped.startswith(('Args:', 'Returns:', 'Raises:', 'Yields:',
                                   'Examples:', 'Notes:', 'See Also:')):
                formatted.append(f"\n{indent_str}**{stripped}**\n")
            elif in_code_block:
                formatted.append(indent_str + line)
            else:
                formatted.append(indent_str + stripped)

        return '\n'.join(formatted)

    def generate_function_markdown(self, func: FunctionDoc, indent: int = 0) -> str:
        """生成函数的Markdown文档"""
        indent_str = ' ' * indent
        md = []

        # 函数签名
        if func.is_method:
            if func.is_static:
                decorator = '@staticmethod'
            elif func.is_classmethod:
                decorator = '@classmethod'
            else:
                decorator = ''

            if decorator:
                md.append(f"{indent_str}{decorator}")

        md.append(f"{indent_str}#### `{func.name}{func.signature}`\n")

        # 文档字符串
        md.append(self.format_docstring(func.docstring, indent))

        return '\n'.join(md)

    def generate_class_markdown(self, cls: ClassDoc) -> str:
        """生成类的Markdown文档"""
        md = []

        # 类名和继承
        if cls.bases:
            inheritance = f"({', '.join(cls.bases)})"
        else:
            inheritance = ""

        md.append(f"### `{cls.name}{inheritance}`\n")

        # 类文档字符串
        md.append(self.format_docstring(cls.docstring))

        # 属性
        if cls.attributes:
            md.append("\n**属性:**\n")
            for attr in cls.attributes:
                md.append(f"- `{attr}`")

        # 方法
        if cls.methods:
            md.append("\n**方法:**\n")
            for method in sorted(cls.methods, key=lambda m: m.name):
                if not method.name.startswith('__'):  # 跳过魔术方法
                    md.append(self.generate_function_markdown(method))
                    md.append("")

        return '\n'.join(md)

    def generate_module_markdown(self, module: ModuleDoc) -> str:
        """生成模块的Markdown文档"""
        md = []

        # 模块标题
        md.append(f"# {module.name}\n")
        md.append(f"**文件:** `{module.path}`\n")

        # 模块文档字符串
        if module.docstring:
            md.append(self.format_docstring(module.docstring))
            md.append("")

        # 类
        if module.classes:
            md.append("## 类\n")
            for cls in sorted(module.classes, key=lambda c: c.name):
                md.append(self.generate_class_markdown(cls))
                md.append("\n---\n")

        # 函数
        if module.functions:
            md.append("## 函数\n")
            for func in sorted(module.functions, key=lambda f: f.name):
                md.append(self.generate_function_markdown(func))
                md.append("")

        return '\n'.join(md)

    def generate_index(self) -> str:
        """生成API索引"""
        md = []

        md.append("# HydroClaude API 参考\n")
        md.append("本文档由自动化工具生成，提供HydroClaude项目的完整API参考。\n")

        # 按模块分组
        core_modules = [m for name, m in self.modules.items() if name.startswith('core')]
        control_modules = [m for name, m in self.modules.items() if name.startswith('control')]
        utils_modules = [m for name, m in self.modules.items() if name.startswith('utils')]
        other_modules = [m for name, m in self.modules.items()
                        if not any(name.startswith(p) for p in ['core', 'control', 'utils'])]

        def add_module_list(title: str, modules: List[ModuleDoc]):
            if modules:
                md.append(f"## {title}\n")
                for module in sorted(modules, key=lambda m: m.name):
                    # 统计
                    n_classes = len(module.classes)
                    n_functions = len(module.functions)
                    description = module.docstring.split('\n')[0] if module.docstring else "无描述"

                    md.append(f"### [{module.name}]({module.name.replace('.', '_')}.md)")
                    md.append(f"{description}\n")
                    md.append(f"- **类:** {n_classes}")
                    md.append(f"- **函数:** {n_functions}\n")

        add_module_list("核心模块 (Core)", core_modules)
        add_module_list("控制模块 (Control)", control_modules)
        add_module_list("工具模块 (Utils)", utils_modules)
        add_module_list("其他模块", other_modules)

        return '\n'.join(md)

    def generate_markdown(self, output_dir: str):
        """生成Markdown文档"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        print(f"\n生成API文档到: {output_path}")

        # 生成索引
        index_md = self.generate_index()
        index_file = output_path / 'API_INDEX.md'
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(index_md)
        print(f"   {index_file.name}")

        # 生成各模块文档
        for module_name, module in self.modules.items():
            module_md = self.generate_module_markdown(module)
            filename = module_name.replace('.', '_') + '.md'
            filepath = output_path / filename

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(module_md)
            print(f"   {filename}")

        print(f"\n成功生成 {len(self.modules) + 1} 个文档文件")

    def generate_summary_stats(self) -> Dict[str, Any]:
        """生成统计摘要"""
        total_classes = sum(len(m.classes) for m in self.modules.values())
        total_functions = sum(len(m.functions) for m in self.modules.values())
        total_methods = sum(
            sum(len(c.methods) for c in m.classes)
            for m in self.modules.values()
        )

        return {
            'total_modules': len(self.modules),
            'total_classes': total_classes,
            'total_functions': total_functions,
            'total_methods': total_methods,
            'modules_by_package': self._group_modules_by_package()
        }

    def _group_modules_by_package(self) -> Dict[str, int]:
        """按包分组模块数量"""
        packages = {}
        for module_name in self.modules.keys():
            package = module_name.split('.')[0] if '.' in module_name else 'root'
            packages[package] = packages.get(package, 0) + 1
        return packages


if __name__ == "__main__":
    # 测试代码
    print("=" * 80)
    print("API文档生成器测试")
    print("=" * 80)

    # 设置项目根目录
    project_root = '/home/user/HydroClaude'

    # 创建生成器
    generator = APIDocGenerator(
        project_root,
        exclude_patterns=[
            '__pycache__', '.git', 'venv', 'env',
            '.pytest_cache', 'build', 'dist',
            'examples', 'tests', 'docs'  # 排除示例和测试
        ]
    )

    # 扫描模块
    generator.scan_modules()

    # 生成统计
    stats = generator.generate_summary_stats()
    print("\n" + "=" * 80)
    print("统计信息:")
    print("=" * 80)
    print(f"  总模块数: {stats['total_modules']}")
    print(f"  总类数: {stats['total_classes']}")
    print(f"  总函数数: {stats['total_functions']}")
    print(f"  总方法数: {stats['total_methods']}")
    print(f"\n按包分组:")
    for package, count in sorted(stats['modules_by_package'].items()):
        print(f"    {package}: {count} 个模块")

    # 生成Markdown文档
    output_dir = os.path.join(project_root, 'docs', 'api')
    generator.generate_markdown(output_dir)

    print("\n" + "=" * 80)
    print("API文档生成完成！")
    print(f"文档位置: {output_dir}")
    print("=" * 80)
