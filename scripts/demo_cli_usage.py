#!/usr/bin/env python3
"""
DeepAnalyze CLI 使用演示脚本
展示各种CLI命令的实际使用方法
"""

import subprocess
import sys
import os

def run_cli_command(command, description):
    """运行CLI命令并显示结果"""
    print(f"\n📍 {description}")
    print(f"🔧 命令: {command}")
    print("-" * 50)
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd="/home/huangzw/Project/DeepAnalyze/src/cli"
        )
        
        if result.returncode == 0:
            print("✅ 执行成功")
            if result.stdout:
                print("📄 输出:")
                print(result.stdout)
        else:
            print("❌ 执行失败")
            if result.stderr:
                print("📄 错误信息:")
                print(result.stderr)
                
    except Exception as e:
        print(f"❌ 命令执行异常: {e}")

def main():
    """主演示函数"""
    print("🚀 DeepAnalyze CLI 模式使用演示")
    print("=" * 60)
    
    # 检查环境
    print("🔍 环境检查...")
    if not os.path.exists("/home/huangzw/Project/DeepAnalyze/src/cli/api_cli_ZH.py"):
        print("❌ 未找到CLI工具")
        return False
    
    # 演示命令列表
    demo_commands = [
        # 帮助命令
        ("python api_cli_ZH.py --help", "查看主帮助信息"),
        ("python api_cli_ZH.py direct --help", "查看直接模式帮助"),
        
        # 基础功能演示（使用示例数据）
        ("python api_cli_ZH.py direct analyze --help", "查看数据分析命令帮助"),
        ("python api_cli_ZH.py direct visualize --help", "查看可视化命令帮助"),
        ("python api_cli_ZH.py direct report --help", "查看报告生成命令帮助"),
        
        # 实际数据分析示例（如果有示例数据）
        # ("python api_cli_ZH.py direct analyze --data-file ../../data/examples/simpson_paradox_docs/analysis/data/Simpson.csv --docs/analysis-type descriptive", "分析Simpson悖论数据"),
    ]
    
    # 执行演示
    for command, description in demo_commands:
        run_cli_command(command, description)
    
    # 使用说明
    print("\n" + "=" * 60)
    print("📚 CLI 使用说明")
    print("=" * 60)
    
    usage_data/exampless = """
📊 常用数据分析命令：

1. 描述性统计分析：
   python api_cli_ZH.py direct analyze \\
       --data-file your_data.csv \\
       --docs/analysis-type descriptive \\
       --output-format html

2. 相关性分析：
   python api_cli_ZH.py direct analyze \\
       --data-file your_data.csv \\
       --docs/analysis-type correlation \\
       --columns age,income,score

3. 生成散点图：
   python api_cli_ZH.py direct visualize \\
       --data-file your_data.csv \\
       --chart-type scatter \\
       --x-column age \\
       --y-column income

4. 创建学术报告：
   python api_cli_ZH.py direct report \\
       --data-file your_data.csv \\
       --temporarylate academic \\
       --output-file report.pdf

5. AI智能问答：
   python api_cli_ZH.py direct chat \\
       --query "数据中有什么有趣的发现？"

📁 数据文件要求：
- 支持格式：CSV, Excel, JSON
- 建议编码：UTF-8
- 列名应具有描述性

⚙️ 环境要求：
- Python 3.8+
- 必要的依赖包已安装
- 对于容器功能需要Docker权限
"""
    
    print(usage_data/exampless)
    
    print("\n💡 提示：")
    print("- 使用 --help 查看每个命令的详细参数")
    print("- 直接模式无需启动src/api服务器")
    print("- 可以组合多个命令实现完整分析流程")
    print("- 结果默认保存在当前目录")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)