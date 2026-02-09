#!/usr/bin/env python3
"""
直接触发LLM分析流程 - 绕过依赖问题
"""

import os
import sys
from pathlib import Path
import json
import time

# 设置环境变量
os.environ['DEEPANALYZE_USE_ORCHESTRATOR'] = '1'
os.environ['DEEPANALYZE_MAX_DEPTH'] = '3'

# 添加项目路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

print("🚀 启动LLM驱动的完整分析流程")
print("=" * 50)

try:
    # 导入必要的模块
    from src.api.config import USE_ORCHESTRATOR, MAX_RECURSION_DEPTH, WORKSPACE_BASE_DIR
    from src.core.orchestration.runner import run_orchestrated_docs_analysis
    
    print(f"🤖 LLM编排模式: {'启用' if USE_ORCHESTRATOR else '禁用'}")
    print(f"🔄 最大递归深度: {MAX_RECURSION_DEPTH}")
    print(f"📁 工作空间目录: {WORKSPACE_BASE_DIR}")
    
    # 创建会话ID
    session_id = f"llm_analysis_{int(time.time())}"
    print(f"📝 会话ID: {session_id}")
    
    # 准备配置
    config = {
        "max_depth": MAX_RECURSION_DEPTH,
        "report_format": "html",
        "report_language": "zh",
        "docs/analysis_types": ["descriptive", "inferential", "correlation", "predictive"],
        "docs/analysis_goal": "全面分析Simpson悖论数据集，识别统计陷阱并提供深入洞察"
    }
    
    print("\n🧠 开始LLM编排分析...")
    print("预计流程:")
    print("1. 文件理解与摘要生成")
    print("2. 数据质量评估") 
    print("3. 智能假设规划")
    print("4. 自主代码生成")
    print("5. 执行与结果分析")
    print("6. 深度洞察提取")
    print("7. 专业报告生成")
    
    # 执行LLM编排分析
    print("\n⏳ 正在执行分析...")
    state = run_orchestrated_docs_analysis(
        session_id=session_id,
        config=config
    )
    
    print("\n✅ LLM分析完成!")
    
    # 显示结果摘要
    print("\n📊 分析结果摘要:")
    if "plan" in state:
        print(f"📋 分析计划: {state['plan'][:200]}..." if len(state['plan']) > 200 else state['plan'])
    
    if "docs/analysis_results" in state:
        print(f"🔍 分析结果: {state['docs/analysis_results'][:200]}..." if len(state['docs/analysis_results']) > 200 else state['docs/analysis_results'])
    
    if "report" in state:
        print(f"📄 生成报告: {len(state['report'])} 字符")
    
    # 保存结果
    results_dir = Path(WORKSPACE_BASE_DIR) / session_id
    results_dir.mkdir(parents=True, exist_ok=True)
    
    result_file = results_dir / "llm_analysis_results.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "session_id": session_id,
            "config": config,
            "results": state,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 结果已保存到: {result_file}")
    print(f"📁 会话目录: {results_dir}")
    
    # 显示下一步操作
    print("\n🎯 下一步操作:")
    print("1. 查看详细分析报告")
    print("2. 检查生成的可视化图表") 
    print("3. 审阅分析假设和洞察")
    print("4. 导出最终分析成果")
    
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("可能是依赖库问题，尝试安装必要组件...")
    
    # 尝试安装必要依赖
    try:
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "langchain", "openai"])
        print("✅ 必要依赖安装完成，请重新运行脚本")
    except Exception as install_error:
        print(f"❌ 依赖安装失败: {install_error}")
        
except Exception as e:
    print(f"❌ 分析执行出错: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 50)
print("✨ LLM分析流程执行完毕")