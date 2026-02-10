"""
AI Assistant Enhancement Tests and Examples
AI助手增强功能测试和示例
"""

from src.core.assistant.engine import (
    AIAssistantEngine,
    IntentType,
    ResponseStyle,
    ContextMode,
    chat_with_assistant
)
from src.core.assistant.context_manager import (
    ContextManager,
    MemoryType,
    get_ai_assistant
)
import time


def demo_context_management():
    """演示上下文管理功能"""
    print("=== 上下文管理功能演示 ===")
    
    # 创建上下文管理器
    cm = ContextManager()
    session_id = "test_session_001"
    
    # 创建对话上下文
    context = cm.create_conversation_context(
        session_id,
        context_mode=ContextMode.HYBRID,
        max_context_length=5000
    )
    print(f"创建会话上下文: {session_id}")
    
    # 添加消息
    messages = [
        "你好，我想分析一些销售数据",
        "我的数据包含日期、销售额和产品类别",
        "请帮我找出销售额的趋势和主要影响因素"
    ]
    
    for i, msg in enumerate(messages):
        message = cm.add_message(session_id, "user", msg)
        print(f"添加消息 {i+1}: {msg[:30]}...")
    
    # 获取格式化消息
    formatted_messages = cm.get_context_messages(session_id)
    print(f"获取到 {len(formatted_messages)} 条格式化消息")
    
    # 添加记忆
    cm.add_memory(
        session_id,
        MemoryType.PREFERENCE,
        "analysis_focus",
        "趋势分析和影响因素",
        importance_score=0.8
    )
    
    cm.add_memory(
        session_id,
        MemoryType.FACT,
        "data_columns",
        ["date", "sales", "product_category"],
        importance_score=0.9
    )
    
    # 搜索记忆
    memories = cm.search_memories(session_id, "分析")
    print(f"搜索到 {len(memories)} 条相关记忆")
    
    return session_id


def demo_intent_classification():
    """演示意图分类功能"""
    print("\n=== 意图分类功能演示 ===")
    
    engine = AIAssistantEngine()
    
    test_messages = [
        ("请分析这份销售数据的趋势", IntentType.DATA_ANALYSIS),
        ("帮我写一段Python代码来处理CSV文件", IntentType.CODE_GENERATION),
        ("我想创建一个销售趋势的折线图", IntentType.VISUALIZATION),
        ("请生成一份季度销售分析报告", IntentType.REPORT_GENERATION),
        ("怎么上传数据文件？", IntentType.HELP_REQUEST),
        ("今天天气怎么样？", IntentType.GENERAL_CHAT)
    ]
    
    correct_predictions = 0
    
    for message, expected_intent in test_messages:
        predicted_intent = engine._classify_intent(message)
        is_correct = predicted_intent == expected_intent
        if is_correct:
            correct_predictions += 1
        
        print(f"消息: {message}")
        print(f"预期: {expected_intent.value}, 预测: {predicted_intent.value}, {'✓' if is_correct else '✗'}")
        print()
    
    accuracy = correct_predictions / len(test_messages)
    print(f"意图分类准确率: {accuracy:.1%} ({correct_predictions}/{len(test_messages)})")


def demo_conversation_flow():
    """演示完整对话流程"""
    print("\n=== 完整对话流程演示 ===")
    
    session_id = "conv_test_" + str(int(time.time()))
    print(f"会话ID: {session_id}")
    
    conversation = [
        "你好，我有一些销售数据想要分析",
        "数据包含月份、销售额和地区信息",
        "请帮我分析各地区销售表现的差异",
        "能否生成相应的可视化图表？",
        "我还想了解销售额的季节性趋势"
    ]
    
    engine = AIAssistantEngine()
    
    for i, user_message in enumerate(conversation, 1):
        print(f"\n--- 第{i}轮对话 ---")
        print(f"用户: {user_message}")
        
        response = engine.process_message(
            session_id,
            user_message,
            context_mode=ContextMode.HYBRID
        )
        
        print(f"助手: {response['content'][:100]}...")
        print(f"意图: {response['intent']}")
        print(f"置信度: {response['confidence']:.2f}")
        print(f"使用上下文: {response['context_used']} 条消息")


def demo_memory_system():
    """演示记忆系统功能"""
    print("\n=== 记忆系统功能演示 ===")
    
    cm = ContextManager()
    session_id = "memory_test_" + str(int(time.time()))
    
    # 创建上下文
    cm.create_conversation_context(session_id)
    
    # 添加不同类型的记忆
    memories_to_add = [
        (MemoryType.PREFERENCE, "report_style", "学术风格", 0.9),
        (MemoryType.FACT, "last_data_type", "时间序列数据", 0.8),
        (MemoryType.CONTEXTUAL, "current_topic", "销售数据分析", 0.7),
        (MemoryType.SKILL, "user_proficiency", "中级水平", 0.6)
    ]
    
    for mem_type, key, value, score in memories_to_add:
        memory = cm.add_memory(session_id, mem_type, key, value, score)
        print(f"添加记忆: {mem_type.value} - {key}: {value} (重要性: {score})")
    
    # 搜索记忆
    print("\n搜索相关记忆:")
    search_results = cm.search_memories(session_id, "分析", [MemoryType.PREFERENCE, MemoryType.CONTEXTUAL])
    for memory in search_results:
        print(f"  - {memory.type.value}: {memory.key} = {memory.value}")


def demo_response_styles():
    """演示不同响应风格"""
    print("\n=== 响应风格演示 ===")
    
    session_id = "style_test_" + str(int(time.time()))
    message = "请分析这份客户满意度调查数据"
    
    engine = AIAssistantEngine()
    
    styles = [
        (ResponseStyle.ANALYTICAL, "分析型"),
        (ResponseStyle.TECHNICAL, "技术型"),
        (ResponseStyle.EXECUTIVE, "执行型"),
        (ResponseStyle.CONVERSATIONAL, "对话型")
    ]
    
    for style, style_name in styles:
        print(f"\n{style_name}响应:")
        response = engine.process_message(
            session_id,
            message,
            style_preference=style
        )
        # 只显示前100个字符
        print(f"  {response['content'][:100]}...")


def demo_error_handling():
    """演示错误处理功能"""
    print("\n=== 错误处理演示 ===")
    
    # 测试无效会话ID
    try:
        response = chat_with_assistant("invalid_session", "测试消息")
        print("无效会话处理: 正常响应")
    except Exception as e:
        print(f"无效会话处理: 出现错误 - {e}")
    
    # 测试空消息
    try:
        response = chat_with_assistant("test_session", "")
        print("空消息处理: 正常响应")
    except Exception as e:
        print(f"空消息处理: 出现错误 - {e}")


def performance_test():
    """性能测试"""
    print("\n=== 性能测试 ===")
    
    import time
    
    session_id = "perf_test_" + str(int(time.time()))
    engine = AIAssistantEngine()
    
    # 测试大量消息处理
    start_time = time.time()
    
    for i in range(20):
        message = f"测试消息 {i+1}: 关于数据分析的第{i+1}个问题"
        response = engine.process_message(session_id, message)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"处理20条消息耗时: {duration:.2f}秒")
    print(f"平均每条消息: {duration_20:.3f}秒")
    
    # 测试上下文长度
    context = engine.context_manager.get_context(session_id)
    if context:
        print(f"最终上下文包含: {len(context.messages)} 条消息")


if __name__ == "__main__":
    print("DeepAnalyze AI助手增强功能演示")
    print("=" * 50)
    
    try:
        # 执行所有演示
        demo_context_management()
        demo_intent_classification()
        demo_conversation_flow()
        demo_memory_system()
        demo_response_styles()
        demo_error_handling()
        performance_test()
        
        print("\n" + "=" * 50)
        print("🎉 所有演示完成！")
        print("\nAI助手增强功能特点:")
        print("✅ 智能意图识别和分类")
        print("✅ 上下文感知对话管理")
        print("✅ 多样化的响应风格")
        print("✅ 记忆系统和个性化")
        print("✅ 完善的错误处理机制")
        print("✅ 性能优化和可扩展性")
        
    except Exception as e:
        print(f"演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
