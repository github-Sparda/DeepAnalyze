#!/usr/bin/env python3
"""
修复重构后的导入路径问题
"""

import os
import re
from pathlib import Path

def fix_import_paths(root_dir):
    """修复导入路径"""
    root_path = Path(root_dir)
    
    # 导入路径映射
    import_mappings = {
        'src.api.': '',  # 移除src.api前缀，使用相对导入
        'src.core.': '', # 移除src.core前缀
    }
    
    # 遍历所有Python文件
    for py_file in root_path.rglob("*.py"):
        try:
            content = py_file.read_text(encoding='utf-8')
            original_content = content
            
            # 修复导入路径
            for old_prefix, new_prefix in import_mappings.items():
                # 匹配 from src.xxx 和 import src.xxx
                pattern = rf'(from\s+|import\s+){re.escape(old_prefix)}(\w+)'
                replacement = rf'\1{new_prefix}\2'
                content = re.sub(pattern, replacement, content)
            
            # 如果内容有变化，写回文件
            if content != original_content:
                py_file.write_text(content, encoding='utf-8')
                print(f"✅ 修复导入路径: {py_file}")
                
        except Exception as e:
            print(f"❌ 处理文件失败 {py_file}: {e}")

def create_api_symlink():
    """创建API模块的符号链接以便兼容"""
    api_source = Path("../api")
    api_target = Path("api")
    
    if not api_target.exists() and api_source.exists():
        try:
            os.symlink(api_source.resolve(), api_target)
            print(f"✅ 创建API符号链接: {api_target} → {api_source}")
        except Exception as e:
            print(f"❌ 创建符号链接失败: {e}")

if __name__ == "__main__":
    # 在src/core目录下运行
    current_dir = Path.cwd()
    print(f"当前目录: {current_dir}")
    
    if current_dir.name == "core" and (current_dir.parent / "src").exists():
        fix_import_paths(".")
        create_api_symlink()
        print("🎉 导入路径修复完成!")
    else:
        print("❌ 请在src/core目录下运行此脚本")