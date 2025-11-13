#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
回滚修改并正确修复
只修复真正有问题的导入，不注释废弃但工作的代码
"""

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime
import json

PROJECT_ROOT = Path(__file__).parent
BACKUP_DIR = PROJECT_ROOT / "backups"

def find_latest_backup():
    """找到最新的备份目录"""
    if not BACKUP_DIR.exists():
        print("[ERROR] No backup directory found")
        return None
    
    backup_dirs = [d for d in BACKUP_DIR.iterdir() if d.is_dir()]
    if not backup_dirs:
        print("[ERROR] No backup found")
        return None
    
    # 按时间排序，返回最新的
    latest = max(backup_dirs, key=lambda d: d.stat().st_mtime)
    return latest

def rollback_from_backup(backup_dir):
    """从备份恢复文件"""
    print(f"\n[ROLLBACK] Restoring from: {backup_dir}")
    
    restored_count = 0
    
    for backup_file in backup_dir.rglob("*.bak"):
        # 获取原始文件路径
        relative_path = backup_file.relative_to(backup_dir)
        # 去掉 .bak 和时间戳后缀
        original_name = backup_file.stem.rsplit('.', 1)[0] + backup_file.suffixes[0]
        original_path = PROJECT_ROOT / relative_path.parent / original_name
        
        if original_path.exists():
            # 恢复文件
            shutil.copy2(backup_file, original_path)
            restored_count += 1
            print(f"[OK] Restored: {original_path.relative_to(PROJECT_ROOT)}")
    
    print(f"\n[SUCCESS] Restored {restored_count} files")
    return restored_count

def get_module_not_found_errors():
    """从第一轮测试结果中提取ModuleNotFoundError的文件列表"""
    results_file = PROJECT_ROOT / "test_results" / "batch_test_results.json"
    
    if not results_file.exists():
        print("[WARN] Original test results not found")
        return []
    
    with open(results_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    module_errors = []
    
    for result in data.get('results', []):
        if result['status'] in ['failed', 'error']:
            error = result.get('error', '')
            if 'ModuleNotFoundError' in error or 'ImportError' in error:
                module_errors.append({
                    'file': result['file_path'],
                    'error': error[:200]
                })
    
    return module_errors

def create_selective_fix_script():
    """创建选择性修复脚本 - 只修复ModuleNotFoundError"""
    module_errors = get_module_not_found_errors()
    
    print(f"\n[ANALYSIS] Found {len(module_errors)} files with import errors")
    
    script_content = f"""#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
选择性修复脚本 - 只修复确认有ModuleNotFoundError的{len(module_errors)}个文件
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
'''

import sys
import os

# 需要修复的文件列表（只包含真正有导入错误的）
FILES_TO_FIX = [
"""
    
    for item in module_errors:
        script_content += f"    '{item['file']}',\n"
    
    script_content += """
]

def add_sys_path_to_file(file_path):
    '''在文件开头添加sys.path配置'''
    if not os.path.exists(file_path):
        print(f"[SKIP] File not found: {{file_path}}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 检查是否已经有sys.path配置
    if 'sys.path.insert' in content:
        print(f"[SKIP] Already has sys.path: {{file_path}}")
        return False
    
    # 在第一个import之前添加sys.path配置
    lines = content.split('\\n')
    insert_pos = 0
    
    for i, line in enumerate(lines):
        if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('\"\"\"'):
            if 'import' in line:
                insert_pos = i
                break
    
    sys_path_block = [
        "import sys",
        "import os",
        "",
        "# Add project root to sys.path",
        "script_path = os.path.abspath(__file__)",
        "project_root = os.path.dirname(os.path.dirname(script_path)) if 'tests' in script_path or 'examples' in script_path else os.path.dirname(script_path)",
        "if project_root not in sys.path:",
        "    sys.path.insert(0, project_root)",
        ""
    ]
    
    lines = lines[:insert_pos] + sys_path_block + lines[insert_pos:]
    
    # 备份原文件
    backup_path = file_path + f".bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # 保存修改
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write('\\n'.join(lines))
    
    print(f"[OK] Fixed: {{file_path}}")
    return True

def main():
    print("="*70)
    print(" Selective Fix - Only ModuleNotFoundError Files")
    print("="*70)
    print(f"\\nFixing {{len(FILES_TO_FIX)}} files with confirmed import errors...\\n")
    
    fixed_count = 0
    
    for file_path in FILES_TO_FIX:
        if add_sys_path_to_file(file_path):
            fixed_count += 1
    
    print(f"\\n[SUCCESS] Fixed {{fixed_count}} files")
    print("="*70)

if __name__ == '__main__':
    main()
"""
    
    # 保存脚本
    script_file = PROJECT_ROOT / "selective_fix.py"
    with open(script_file, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"[OK] Created selective fix script: {script_file}")
    return script_file

def main():
    print("="*70)
    print(" ROLLBACK AND PROPER FIX")
    print("="*70)
    
    print("\n[STEP 1] Finding latest backup...")
    backup_dir = find_latest_backup()
    
    if not backup_dir:
        print("[ERROR] No backup found, cannot rollback")
        return
    
    print(f"[OK] Found backup: {backup_dir}")
    
    # 询问用户确认
    print("\n[WARNING] This will restore files from backup")
    print("          All manual changes will be lost!")
    response = input("Continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("[ABORT] Rollback cancelled")
        return
    
    print("\n[STEP 2] Rolling back files...")
    restored = rollback_from_backup(backup_dir)
    
    if restored == 0:
        print("[ERROR] No files were restored")
        return
    
    print("\n[STEP 3] Creating selective fix script...")
    fix_script = create_selective_fix_script()
    
    print("\n" + "="*70)
    print(" ROLLBACK COMPLETE")
    print("="*70)
    print(f"\n[NEXT STEPS]")
    print(f"1. Run the selective fix script:")
    print(f"   python {fix_script.name}")
    print(f"2. Test a small sample:")
    print(f"   python quick_test_sample.py -n 20")
    print(f"3. If successful, run full batch test:")
    print(f"   python batch_test_all_cases.py")
    print("")

if __name__ == '__main__':
    main()

