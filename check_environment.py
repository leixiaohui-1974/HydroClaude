#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
环境检查脚本

检查测试所需的所有依赖是否已安装。
"""

import sys

def check_environment():
    """检查环境"""
    print("="*70)
    print("HydroClaude测试环境检查")
    print("="*70)
    
    missing = []
    
    # 检查Python版本
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"\nPython版本: {python_version}")
    if sys.version_info < (3, 7):
        print("❌ Python版本过低，需要>=3.7")
        missing.append("Python>=3.7")
    else:
        print("✓ Python版本满足要求")
    
    # 检查依赖
    dependencies = [
        ('numpy', '数值计算'),
        ('scipy', '科学计算'),
        ('matplotlib', '可视化'),
        ('yaml', 'YAML解析'),
    ]
    
    print("\n检查依赖:")
    for module_name, desc in dependencies:
        try:
            if module_name == 'yaml':
                import yaml
                module = yaml
            else:
                module = __import__(module_name)
            
            version = getattr(module, '__version__', 'unknown')
            print(f"✓ {module_name:12s} {version:10s} ({desc})")
        except ImportError:
            print(f"❌ {module_name:12s} {'未安装':10s} ({desc})")
            missing.append(module_name)
    
    # 可选依赖
    optional_deps = [
        ('pandas', '数据分析'),
        ('seaborn', '高级可视化'),
    ]
    
    print("\n可选依赖:")
    for module_name, desc in optional_deps:
        try:
            module = __import__(module_name)
            version = getattr(module, '__version__', 'unknown')
            print(f"✓ {module_name:12s} {version:10s} ({desc})")
        except ImportError:
            print(f"⚠ {module_name:12s} {'未安装':10s} ({desc}) [可选]")
    
    # 总结
    print("\n" + "="*70)
    if missing:
        print(f"❌ 缺少{len(missing)}个必需依赖")
        print("\n安装命令:")
        print(f"  pip3 install {' '.join(missing)}")
        print("\n或使用:")
        print("  pip3 install -r requirements.txt")
        return False
    else:
        print("✅ 所有必需依赖已就绪")
        print("\n可以运行测试:")
        print("  python3 run_comprehensive_tests.py --week 1")
        return True


if __name__ == '__main__':
    success = check_environment()
    sys.exit(0 if success else 1)
