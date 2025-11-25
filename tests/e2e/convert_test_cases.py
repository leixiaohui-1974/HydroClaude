#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
将后端测试案例转换为Web端到端测试输入格式

Author: HydroClaude Team
Date: 2025-11-15
"""

import json
import warnings
warnings.filterwarnings("ignore")
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestCaseConverter:
    """测试案例转换器"""
    
    def __init__(self):
        self.examples_dir = project_root / "examples"
        self.output_dir = project_root / "tests" / "e2e" / "test_cases"
        self.test_cases = []
    
    def scan_backend_examples(self) -> List[Path]:
        """扫描后端示例脚本"""
        scripts = []
        
        # 扫描examples目录
        if self.examples_dir.exists():
            for script_file in self.examples_dir.rglob("*.py"):
                # 排除__init__.py和工具脚本
                if script_file.name != "__init__.py" and not script_file.name.startswith("_"):
                    scripts.append(script_file)
        
        print(f"✅ 找到 {len(scripts)} 个后端测试脚本")
        return scripts
    
    def extract_config_from_script(self, script_path: Path) -> Dict[str, Any]:
        """从脚本中提取配置参数"""
        try:
            with open(script_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取基本参数
            config = {
                "name": script_path.stem,
                "description": self._extract_description(content),
                "type": self._detect_test_type(script_path.name),
                "parameters": self._extract_parameters(content)
            }
            
            return config
        
        except Exception as e:
            print(f"⚠️  解析失败 {script_path.name}: {e}")
            return None
    
    def _extract_description(self, content: str) -> str:
        """提取脚本描述"""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '"""' in line and i < 20:
                # 找到文档字符串
                desc_lines = []
                for j in range(i+1, min(i+10, len(lines))):
                    if '"""' in lines[j]:
                        break
                    desc_lines.append(lines[j].strip())
                return ' '.join(desc_lines)
        return "无描述"
    
    def _detect_test_type(self, filename: str) -> str:
        """检测测试类型"""
        filename_lower = filename.lower()
        
        if 'gate' in filename_lower or 'sluice' in filename_lower:
            return "sluice_gate"
        elif 'weir' in filename_lower:
            return "weir"
        elif 'orifice' in filename_lower:
            return "orifice"
        elif 'steady' in filename_lower or 'uniform' in filename_lower:
            return "steady_flow"
        elif 'unsteady' in filename_lower or 'transient' in filename_lower:
            return "unsteady_flow"
        elif 'subcritical' in filename_lower:
            return "subcritical"
        elif 'supercritical' in filename_lower:
            return "supercritical"
        elif 'hydraulic_jump' in filename_lower or 'jump' in filename_lower:
            return "hydraulic_jump"
        else:
            return "basic"
    
    def _extract_parameters(self, content: str) -> Dict[str, Any]:
        """提取参数（简化版本）"""
        params = {
            "length": 10000.0,
            "width": 10.0,
            "slope": 0.001,
            "roughness": 0.025,
            "flow_rate": 50.0,
            "nx": 500,
            "structures": []
        }
        
        # 尝试提取常见参数
        import re
        
        # 提取长度
        match = re.search(r'length\s*=\s*([\d.]+)', content)
        if match:
            params["length"] = float(match.group(1))
        
        # 提取宽度
        match = re.search(r'width\s*=\s*([\d.]+)', content)
        if match:
            params["width"] = float(match.group(1))
        
        # 提取坡度
        match = re.search(r'slope\s*=\s*([\d.eE-]+)', content)
        if match:
            params["slope"] = float(match.group(1))
        
        # 提取糙率
        match = re.search(r'roughness\s*=\s*([\d.]+)', content)
        if match:
            params["roughness"] = float(match.group(1))
        
        # 提取流量
        match = re.search(r'flow_rate\s*=\s*([\d.]+)', content)
        if match:
            params["flow_rate"] = float(match.group(1))
        
        return params
    
    def convert_to_web_input(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """转换为Web系统输入格式"""
        web_input = {
            "version": "2.0.0",
            "name": config["name"],
            "description": config["description"],
            "type": config["type"],
            "canal": {
                "length": config["parameters"]["length"],
                "width": config["parameters"]["width"],
                "slope": config["parameters"]["slope"],
                "roughness": config["parameters"]["roughness"],
                "nx": config["parameters"]["nx"]
            },
            "flow": {
                "flow_rate": config["parameters"]["flow_rate"],
                "type": "steady"
            },
            "structures": config["parameters"]["structures"],
            "solver": {
                "type": "hydrostatic",
                "max_iter": 100,
                "convergence_tol": 0.1
            },
            "output": {
                "save_plots": True,
                "save_data": True,
                "formats": ["json", "csv"]
            }
        }
        
        return web_input
    
    def save_test_case(self, test_case: Dict[str, Any], index: int):
        """保存测试案例"""
        filename = f"test_case_{index:03d}_{test_case['name']}.json"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(test_case, f, ensure_ascii=False, indent=2)
        
        print(f"  💾 保存: {filename}")
    
    def generate_test_index(self):
        """生成测试案例索引"""
        index = {
            "total": len(self.test_cases),
            "cases": []
        }
        
        for i, case in enumerate(self.test_cases):
            index["cases"].append({
                "id": i + 1,
                "name": case["name"],
                "type": case["type"],
                "description": case["description"],
                "file": f"test_case_{i+1:03d}_{case['name']}.json"
            })
        
        index_file = self.output_dir / "test_index.json"
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 生成测试索引: {index_file}")
        print(f"   总共 {index['total']} 个测试案例")
    
    def run(self):
        """执行转换"""
        print("=" * 60)
        print("🔄 开始转换后端测试案例")
        print("=" * 60)
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 扫描脚本
        scripts = self.scan_backend_examples()
        
        # 转换每个脚本
        print(f"\n📝 转换测试案例:")
        for i, script in enumerate(scripts[:100], 1):  # 限制前100个
            config = self.extract_config_from_script(script)
            if config:
                web_input = self.convert_to_web_input(config)
                self.test_cases.append(web_input)
                self.save_test_case(web_input, i)
        
        # 生成索引
        self.generate_test_index()
        
        print("\n" + "=" * 60)
        print("✅ 转换完成！")
        print("=" * 60)


if __name__ == "__main__":
    converter = TestCaseConverter()
    converter.run()
