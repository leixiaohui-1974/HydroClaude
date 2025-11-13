#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
完整清理所有emoji - 扩展到整个项目
"""

import os
import re
import sys

# Emoji匹配模式（4字节UTF-8）
EMOJI_PATTERN = re.compile(
    r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF'
    r'\U0001F1E0-\U0001F1FF\u2600-\u26FF\u2700-\u27BF]',
    re.UNICODE
)

# 要清理的目录（排除虚拟环境和node_modules）
TARGET_DIRS = [
    '.',  # 项目根目录
]

EXCLUDE_PATTERNS = [
    'venv', 'env', '.venv', 
    'node_modules', 
    '.git',
    '__pycache__',
    'remove_all_emojis',  # 排除清理脚本本身
]

def should_process(filepath):
    """判断是否应该处理该文件"""
    # 排除特定路径
    for exclude in EXCLUDE_PATTERNS:
        if exclude in filepath:
            return False
    # 只处理Python文件
    return filepath.endswith('.py')

def remove_emojis_from_file(filepath):
    """从文件中移除emoji"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找emoji
        emojis_found = EMOJI_PATTERN.findall(content)
        if not emojis_found:
            return 0
        
        # 移除emoji
        new_content = EMOJI_PATTERN.sub('', content)
        
        # 写回文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return len(emojis_found)
    
    except Exception as e:
        print(f"[!] Error processing {filepath}: {e}")
        return 0

def main():
    """主函数"""
    print("="*60)
    print(" Complete Emoji Removal Tool")
    print("="*60)
    
    total_files = 0
    total_emojis = 0
    modified_files = []
    
    # 遍历所有目标目录
    for target_dir in TARGET_DIRS:
        print(f"\n[*] Scanning {target_dir}...")
        
        for root, dirs, files in os.walk(target_dir):
            # 过滤目录
            dirs[:] = [d for d in dirs if not any(ex in d for ex in EXCLUDE_PATTERNS)]
            
            for file in files:
                filepath = os.path.join(root, file)
                
                if not should_process(filepath):
                    continue
                
                total_files += 1
                emoji_count = remove_emojis_from_file(filepath)
                
                if emoji_count > 0:
                    total_emojis += emoji_count
                    modified_files.append((filepath, emoji_count))
                    print(f"[OK] Cleaned {filepath}: removed {emoji_count} emoji(s)")
    
    # 总结
    print("\n" + "="*60)
    print(" Summary")
    print("="*60)
    print(f"Total files scanned: {total_files}")
    print(f"Files modified: {len(modified_files)}")
    print(f"Total emojis removed: {total_emojis}")
    
    if modified_files:
        print("\n[*] Modified files:")
        for filepath, count in modified_files[:20]:  # 只显示前20个
            print(f"    {filepath}: {count} emoji(s)")
        
        if len(modified_files) > 20:
            print(f"    ... and {len(modified_files) - 20} more")
    
    print("\n[OK] Emoji removal complete!")
    print("="*60)

if __name__ == "__main__":
    main()






