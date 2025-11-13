#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量移除所有Python文件中的emoji字符
"""

import os
import re
import sys

# 常见emoji列表
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols  (包括🚀)
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\u2600-\u26FF"          # misc symbols (包括⚠️✓等)
    "\u2700-\u27BF"          # dingbats
    "]+",
    flags=re.UNICODE
)

# Emoji到ASCII的映射
EMOJI_REPLACEMENTS = {
    '🚀': '[ROCKET]',
    '✓': '[OK]',
    '✗': '[FAIL]',
    '⚠': '[WARN]',
    '⚠️': '[WARN]',
    '🎯': '[TARGET]',
    '💡': '[IDEA]',
    '📊': '[CHART]',
    '⏱': '[TIMER]',
    '🔄': '[RELOAD]',
    '🎉': '[SUCCESS]',
}

def remove_emojis_from_file(filepath):
    """从文件中移除emoji"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        # 先替换已知的emoji
        for emoji, replacement in EMOJI_REPLACEMENTS.items():
            if emoji in content:
                content = content.replace(emoji, replacement)
                modified = True
        
        # 再用正则清理其他emoji
        new_content = EMOJI_PATTERN.sub('', content)
        if new_content != content:
            content = new_content
            modified = True
        
        if modified:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    
    except Exception as e:
        print(f"[ERROR] {filepath}: {e}")
        return False

def process_directory(directory, extensions=['.py']):
    """处理目录中的所有文件"""
    modified_files = []
    
    for root, dirs, files in os.walk(directory):
        # 跳过特定目录
        dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', 'node_modules', 'venv']]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                if remove_emojis_from_file(filepath):
                    modified_files.append(filepath)
                    print(f"[MODIFIED] {filepath}")
    
    return modified_files

def main():
    print("="*80)
    print("Removing Emoji Characters from Python Files")
    print("="*80)
    
    # 处理solvers目录
    print("\n[Processing] solvers/")
    solvers_files = process_directory('solvers', ['.py'])
    
    # 处理web/backend目录
    print("\n[Processing] web/backend/")
    backend_files = process_directory('web/backend', ['.py'])
    
    # 总结
    all_modified = solvers_files + backend_files
    
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    print(f"Total files modified: {len(all_modified)}")
    
    if all_modified:
        print("\nModified files:")
        for f in all_modified:
            print(f"  - {f}")
        
        print("\n[IMPORTANT] Backend service needs to be restarted!")
        print("Run: Restart uvicorn in the terminal")
    else:
        print("\nNo files needed modification.")
    
    print("="*80)

if __name__ == '__main__':
    main()







