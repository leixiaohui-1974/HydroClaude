#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试案例导入问题自动修复工具
Auto-fix tool for test case import issues

自动检测并修复测试案例中的常见导入问题。
Automatically detects and fixes common import issues in test cases.

Author: HydroClaude Team
Date: 2025-11-13
"""

import os
import re
from pathlib import Path
from typing import List, Tuple
import shutil
from datetime import datetime

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
BACKUP_DIR = PROJECT_ROOT / "test_fixes_backup"
BACKUP_DIR.mkdir(exist_ok=True)


# ============================================================================
# Import Fixer
# ============================================================================

class ImportFixer:
    """Fix common import issues in test files"""
    
    def __init__(self, dry_run: bool = True):
        self.dry_run = dry_run
        self.fixes_applied = 0
        self.files_modified = 0
        
    def fix_file(self, file_path: Path) -> Tuple[bool, str]:
        """
        Fix import issues in a single file
        Returns: (was_modified, message)
        """
        if not file_path.exists() or not file_path.suffix == '.py':
            return False, "Not a Python file or doesn't exist"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        except Exception as e:
            return False, f"Failed to read file: {e}"
        
        modified_content = original_content
        changes = []
        
        # Fix 1: Add sys.path configuration if missing
        if 'sys.path' not in modified_content and 'import sys' in modified_content:
            # Insert sys.path configuration after import sys
            sys_path_fix = """
# Add project root to Python path
script_path = os.path.abspath(__file__)
project_root = os.path.dirname(os.path.dirname(script_path))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
"""
            # Find the position after 'import sys'
            import_sys_pattern = r'(import sys\s*\n)'
            if re.search(import_sys_pattern, modified_content):
                modified_content = re.sub(
                    import_sys_pattern,
                    r'\1' + sys_path_fix + '\n',
                    modified_content,
                    count=1
                )
                changes.append("Added sys.path configuration")
        
        # Fix 2: Add missing 'import os' if sys.path fix was added
        if 'os.path.abspath' in modified_content and 'import os' not in modified_content:
            # Add 'import os' after 'import sys'
            modified_content = modified_content.replace(
                'import sys\n',
                'import sys\nimport os\n'
            )
            changes.append("Added missing 'import os'")
        
        # Fix 3: Convert relative imports to absolute for common modules
        relative_import_pattern = r'from \.\.(\w+) import'
        if re.search(relative_import_pattern, modified_content):
            modified_content = re.sub(
                relative_import_pattern,
                r'from \1 import',
                modified_content
            )
            changes.append("Converted relative imports to absolute")
        
        # Fix 4: Add try-except for imports
        solver_import_pattern = r'^(from solvers\.\w+ import .+)$'
        matches = re.findall(solver_import_pattern, modified_content, re.MULTILINE)
        for match in matches:
            if 'try:' not in modified_content[:modified_content.find(match)]:
                # Wrap in try-except
                try_except_wrapper = f"""try:
    {match}
except ImportError as e:
    print(f"Import error: {{e}}")
    print("Make sure project root is in sys.path")
    sys.exit(1)
"""
                modified_content = modified_content.replace(match, try_except_wrapper)
                changes.append(f"Added try-except for: {match[:50]}...")
        
        # Check if any modifications were made
        if modified_content != original_content:
            if not self.dry_run:
                # Backup original file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_path = BACKUP_DIR / f"{file_path.name}.{timestamp}.bak"
                shutil.copy2(file_path, backup_path)
                
                # Write fixed content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)
                
                self.files_modified += 1
                self.fixes_applied += len(changes)
                
                return True, f"Fixed: {', '.join(changes)} (backup: {backup_path.name})"
            else:
                return True, f"[DRY RUN] Would fix: {', '.join(changes)}"
        
        return False, "No issues found"
    
    def fix_directory(self, directory: Path, pattern: str = "**/*.py") -> None:
        """Fix all Python files in a directory"""
        files = list(directory.glob(pattern))
        
        print(f"\nScanning {len(files)} Python files in {directory}...")
        print(f"Mode: {'DRY RUN' if self.dry_run else 'APPLY FIXES'}\n")
        
        for file_path in files:
            # Skip backup files and __pycache__
            if '.bak' in file_path.name or '__pycache__' in str(file_path):
                continue
            
            was_modified, message = self.fix_file(file_path)
            
            if was_modified:
                print(f"[OK] {file_path.relative_to(PROJECT_ROOT)}")
                print(f"  {message}")
    
    def print_summary(self):
        """Print summary of fixes"""
        print("\n" + "="*70)
        print(" IMPORT FIXER SUMMARY ".center(70))
        print("="*70)
        print(f"\nMode: {'DRY RUN (no files modified)' if self.dry_run else 'FIXES APPLIED'}")
        print(f"Files modified: {self.files_modified}")
        print(f"Total fixes: {self.fixes_applied}")
        
        if self.dry_run:
            print("\nℹ️  This was a dry run. Run with --apply to actually fix files.")
        else:
            print(f"\n[OK] Fixes applied! Backups saved to: {BACKUP_DIR}")
        
        print("="*70 + "\n")


# ============================================================================
# Specific Fixes for Common Patterns
# ============================================================================

def fix_sys_path_in_tests():
    """Add sys.path configuration to test files that are missing it"""
    test_dirs = [
        PROJECT_ROOT / "tests",
        PROJECT_ROOT / "examples",
        PROJECT_ROOT / "validation_cases"
    ]
    
    sys_path_template = """import sys
import os

# Add project root to Python path
script_path = os.path.abspath(__file__)
# Adjust path depth based on directory structure
project_root = os.path.dirname(os.path.dirname(script_path))  # For tests/
# project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))  # For deeper nesting
if project_root not in sys.path:
    sys.path.insert(0, project_root)

"""
    
    files_to_fix = []
    
    for test_dir in test_dirs:
        if not test_dir.exists():
            continue
        
        for py_file in test_dir.rglob("*.py"):
            if '__pycache__' in str(py_file) or '.bak' in py_file.name:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if it needs fixing
                if 'from solvers' in content or 'from utils' in content:
                    if 'sys.path' not in content:
                        files_to_fix.append(py_file)
            except Exception as e:
                print(f"Error reading {py_file}: {e}")
    
    return files_to_fix


# ============================================================================
# Main Function
# ============================================================================

def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fix common import issues in HydroClaude test files"
    )
    parser.add_argument(
        '--apply',
        action='store_true',
        help='Apply fixes (default is dry run)'
    )
    parser.add_argument(
        '--directory',
        type=str,
        default='tests',
        help='Directory to scan (default: tests)'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print(" HydroClaude Import Fixer ".center(70))
    print("="*70)
    
    target_dir = PROJECT_ROOT / args.directory
    
    if not target_dir.exists():
        print(f"\n[ERROR] Directory not found: {target_dir}")
        return
    
    fixer = ImportFixer(dry_run=not args.apply)
    fixer.fix_directory(target_dir)
    fixer.print_summary()
    
    # Show files that would be fixed
    if not args.apply:
        print("\nTo apply these fixes, run:")
        print(f"  python fix_test_import_issues.py --apply --directory {args.directory}")


if __name__ == '__main__':
    main()

