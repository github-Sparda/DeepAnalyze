#!/usr/bin/env python3
"""
直接测试LLM API调用
验证是否能成功连接到配置的LLM服务
"""

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 添加项目路径
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

load_dotenv(PROJECT_ROOT / ".env")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test LLM API connectivity and run a small analysis.")
    parser.add_argument("--output-dir", default="outputs/llm_api_test", help="Directory to store outputs")
    args = parser.parse_args()

    output_dir = PROJECT_ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("🔍 测试LLM API连接")
    print("=" * 40)
    
    try:
        # 导入LLM客户端
        from src.core.orchestration.llm import LLMClient
        
        print("✅ 成功导入LLM客户端")
        
        # 创建LLM客户端实例
        llm_client = LLMClient()
        print("✅ 成功创建LLM客户端实例")
        
        # 测试简单消息
        test_messages = [
            {"role": "system", "content": "You are a helpful data analysis assistant."},
            {"role": "user", "content": "简要分析一下什么是Simpson悖论？"}
        ]
        
        print("\n📤 发送测试请求到LLM API...")
        print(f"API地址: {llm_client.client.base_url}")
        
        # 发送请求
        response = llm_client.chat(test_messages, max_tokens=500)
        
        print("\n📥 收到LLM响应:")
        print("-" * 40)
        print(response)
        print("-" * 40)
        
        print("\n✅ LLM API连接测试成功!")
        
        # 如果API连接成功，执行完整的数据分析
        print("\n🚀 开始完整的LLM数据分析流程...")
        
        # 准备数据分析消息
        analysis_messages = [
            {"role": "system", "content": "You are DeepAnalyze, an expert data scientist. Provide detailed analysis in Chinese."},
            {"role": "user", "content": """请分析以下Simpson悖论数据集：

数据背景：这是一个关于治疗效果的研究数据
变量包括：treatment(治疗组), success(成功率), dept(部门)

请提供：
1. 数据概览和基本统计
2. Simpson悖论的识别和解释
3. 统计分析建议
4. 实际业务含义

请用专业的数据科学语言回答。"""}
        ]
        
        print("📤 发送数据分析请求...")
        analysis_response = llm_client.chat(analysis_messages, max_tokens=2000)
        
        print("\n📊 LLM数据分析结果:")
        print("-" * 40)
        print(analysis_response)
        print("-" * 40)
        
        # 保存结果
        import json
        import time
        
        result_data = {
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "test_query": "Simpson悖论解释",
            "analysis_query": "完整数据分析",
            "llm_response": analysis_response,
            "api_endpoint": str(llm_client.client.base_url)
        }
        
        result_file = output_dir / f"llm_analysis_result_{int(time.time())}.json"
        with result_file.open('w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 分析结果已保存到: {result_file}")
        
    except ImportError as e:
        print(f"❌ 导入错误: {e}")
        print("可能是依赖库问题")
        
    except Exception as e:
        print(f"❌ LLM API调用失败: {e}")
        import traceback
        traceback.print_exc()
        
        # 显示配置信息用于调试
        print(f"\n🔧 当前配置信息:")
        try:
            from src.api.config import API_BASE, DEEPANALYZE_VLLM_API_KEY, DEFAULT_MODEL
            print(f"API_BASE: {API_BASE}")
            print(f"API_KEY设置: {bool(DEEPANALYZE_VLLM_API_KEY)}")
            print(f"DEFAULT_MODEL: {DEFAULT_MODEL}")
        except:
            print("无法加载配置信息")

    print("\n" + "=" * 40)
    print("✨ LLM API测试完成")