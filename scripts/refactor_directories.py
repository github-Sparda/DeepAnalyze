#!/usr/bin/env python3
"""
DeepAnalyze 目录结构重构迁移工具
自动化执行目录结构调整和引用更新
"""

import os
import shutil
import re
from pathlib import Path
from datetime import datetime
import json

class DirectoryRefactor:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.backup_dir = self.project_root / "backup" / f"dir_refactor_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.migration_log = []
        
        # 迁移映射关系
        self.migration_map = {
            # 源码迁移
            "src/core": "src/core",
            "src/api": "src/api", 
            "src/cli": "src/cli",
            "src/web": "src/web",
            "src/jupyter": "src/jupyter",
            
            # 数据迁移
            "data/examples": "data/data/exampless",
            "data/examples/benchmarks": "data/data/exampless/benchmarks",
            "data/sessions/active": "data/sessions/active",
            "scripts/data/sessions/active": "data/sessions/active",
            "src/cli/data/sessions/active": "data/sessions/active",
            
            # 缓存和临时文件
            "data/cache": "data/data/cache",
            "temporary": "data/data/cache/temporaryorary",
            "outputs": "outputs",
            "outputs/logs": "outputs/outputs/logs",
            
            # 文档迁移
            "docs/guides/guides": "docs/guides/guides/guides",
            "docs/analysis": "docs/guides/guides/docs/analysis",
            "docs/design": "docs/guides/guides/docs/design",
            "docs/specs": "docs/guides/guides/specs",
            
            # 归档数据
            "data/sessions/archived": "data/sessions/data/sessions/archivedd"
        }
        
        # 需要更新路径引用的文件类型
        self.target_file_types = ['.py', '.md', '.json', '.yaml', '.yml', '.toml', '.sh', '.txt']
        
    def log_action(self, action, source, target=None, status="success"):
        """记录迁移操作"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "source": str(source),
            "target": str(target) if target else None,
            "status": status
        }
        self.migration_log.append(log_entry)
        print(f"[{status.upper()}] {action}: {source}" + (f" → {target}" if target else ""))
    
    def backup_project(self):
        """备份项目"""
        print("📋 开始备份项目...")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份重要文件
        important_files = [
            '.env', 'requirements.txt', 'README.md', 'README.ZH.md'
        ]
        
        for file_name in important_files:
            source = self.project_root / file_name
            if source.exists():
                backup_path = self.backup_dir / file_name
                shutil.copy2(source, backup_path)
                self.log_action("backup_file", source, backup_path)
        
        print(f"✅ 项目备份完成: {self.backup_dir}")
    
    def create_new_structure(self):
        """创建新的目录结构"""
        print("🏗️  创建新目录结构...")
        
        new_dirs = [
            "src/core", "src/api", "src/cli", "src/web", "src/jupyter", "src/utils",
            "data/data/exampless/student_loan", "data/data/exampless/simpson_paradox", "data/data/exampless/benchmarks",
            "data/sessions/active", "data/sessions/data/sessions/archivedd",
            "data/semantic", "data/data/cache/disk", "data/data/cache/temporaryorary",
            "docs/guides/guides/docs/design", "docs/guides/guides/specs", "docs/guides/guides/guides", "docs/guides/guides/api", "docs/guides/guides/tutorials", "docs/guides/guides/docs/analysis",
            "outputs/reports", "outputs/visualizations", "outputs/exports", "outputs/outputs/logs",
            "scripts/dev", "scripts/deploy", "scripts/maintenance", "scripts/tests"
        ]
        
        for dir_path in new_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            self.log_action("create_dir", full_path)
    
    def migrate_directories(self):
        """迁移目录内容"""
        print("🚚 开始目录迁移...")
        
        for source_rel, target_rel in self.migration_map.items():
            source_path = self.project_root / source_rel
            target_path = self.project_root / target_rel
            
            if source_path.exists() and source_path != target_path:
                try:
                    # 如果目标目录已存在，合并内容
                    if target_path.exists():
                        for item in source_path.iterdir():
                            target_item = target_path / item.name
                            if item.is_file():
                                shutil.move(str(item), str(target_item))
                            elif item.is_dir():
                                if target_item.exists():
                                    # 递归合并目录
                                    self.merge_directories(item, target_item)
                                else:
                                    shutil.move(str(item), str(target_item))
                    else:
                        # 直接移动整个目录
                        shutil.move(str(source_path), str(target_path))
                    
                    self.log_action("move_directory", source_path, target_path)
                except Exception as e:
                    self.log_action("move_directory", source_path, target_path, "failed")
                    print(f"❌ 迁移失败 {source_path}: {e}")
    
    def merge_directories(self, source_dir, target_dir):
        """合并两个目录"""
        for item in source_dir.iterdir():
            target_item = target_dir / item.name
            if item.is_file():
                shutil.move(str(item), str(target_item))
            elif item.is_dir():
                if target_item.exists():
                    self.merge_directories(item, target_item)
                else:
                    shutil.move(str(item), str(target_item))
    
    def update_file_references(self):
        """更新文件中的路径引用"""
        print("📝 更新文件路径引用...")
        
        # 构建反向映射用于替换
        reverse_map = {}
        for source, target in self.migration_map.items():
            # 处理相对路径的各种表示形式
            reverse_map[source] = target
            reverse_map[f"./{source}"] = f"./{target}"
            reverse_map[f"../{source}"] = f"../{target}"
        
        # 遍历所有目标文件类型
        for file_path in self.project_root.rglob('*'):
            if file_path.is_file() and file_path.suffix in self.target_file_types:
                self.update_single_file(file_path, reverse_map)
    
    def update_single_file(self, file_path, path_mapping):
        """更新单个文件中的路径引用"""
        try:
            # 读取文件内容
            content = file_path.read_text(encoding='utf-8')
            original_content = content
            
            # 替换路径引用
            for old_path, new_path in path_mapping.items():
                # 多种替换模式
                patterns = [
                    old_path,           # 直接替换
                    f'"{old_path}',     # 引号包围
                    f"'{old_path}",     # 单引号包围
                    f"`{old_path}",     # 反引号包围
                    f"({old_path})",    # 括号包围
                ]
                
                replacements = [
                    new_path,
                    f'"{new_path}',
                    f"'{new_path}",
                    f"`{new_path}",
                    f"({new_path})",
                ]
                
                for pattern, replacement in zip(patterns, replacements):
                    content = content.replace(pattern, replacement)
            
            # 如果内容有变化，写回文件
            if content != original_content:
                file_path.write_text(content, encoding='utf-8')
                self.log_action("update_references", file_path)
                
        except Exception as e:
            self.log_action("update_references", file_path, status="failed")
            print(f"❌ 更新文件失败 {file_path}: {e}")
    
    def cleanup_old_structure(self):
        """清理旧目录结构"""
        print("🧹 清理旧目录结构...")
        
        # 移除空的旧目录
        old_dirs = [
            "src/core", "src/api", "demo", "data/examples", "data/examples/benchmarks", 
            "data/sessions/active", "data/cache", "temporary", "docs/analysis", "docs/design"
        ]
        
        for dir_name in old_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and not any(dir_path.iterdir()):
                try:
                    dir_path.rmdir()
                    self.log_action("remove_empty_dir", dir_path)
                except Exception as e:
                    self.log_action("remove_empty_dir", dir_path, status="failed")
                    print(f"❌ 删除目录失败 {dir_path}: {e}")
    
    def save_migration_log(self):
        """保存迁移日志"""
        log_file = self.backup_dir / "migration_log.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.migration_log, f, indent=2, ensure_ascii=False)
        print(f"📝 迁移日志已保存: {log_file}")
    
    def run_migration(self, dry_run=False):
        """执行完整迁移流程"""
        print("=" * 60)
        print("🚀 DeepAnalyze 目录结构重构工具")
        print("=" * 60)
        print(f"📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📂 项目根目录: {self.project_root}")
        print(f"📋 模拟模式: {'是' if dry_run else '否'}")
        print()
        
        if dry_run:
            print("🔍 模拟迁移模式 - 仅显示将要执行的操作")
            print("迁移映射关系:")
            for source, target in self.migration_map.items():
                print(f"  {source}/ → {target}/")
            return
        
        try:
            # 执行迁移步骤
            self.backup_project()
            self.create_new_structure()
            self.migrate_directories()
            self.update_file_references()
            self.cleanup_old_structure()
            self.save_migration_log()
            
            print("\n🎉 目录重构完成!")
            print("✅ 新结构已生效，请验证各项功能是否正常")
            
        except Exception as e:
            print(f"\n❌ 迁移过程中出现错误: {e}")
            import traceback
            traceback.print_exc()

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='DeepAnalyze 目录结构重构工具')
    parser.add_argument('--dry-run', action='store_true', help='模拟运行，不实际修改文件')
    parser.add_argument('--project-root', default='/home/huangzw/Project/DeepAnalyze', 
                       help='项目根目录路径')
    
    args = parser.parse_args()
    
    refactor = DirectoryRefactor(args.project_root)
    refactor.run_migration(dry_run=args.dry_run)

if __name__ == "__main__":
    main()