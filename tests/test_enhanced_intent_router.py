"""
Enhanced Intent Router Test and Examples
增强意图识别系统的测试用例和使用示例
"""

from orchestration.enhanced_intent_router import (
    EnhancedChatIntent,
    EnhancedRouterDecision,
    enhanced_classify_intent,
    get_intent_recognizer
)


def test_basic_classification():
    """测试基本意图分类"""
    print("=== 基本意图分类测试 ===")
    
    test_cases = [
        # 指导式分析
        ("请分析这份销售数据的趋势", EnhancedChatIntent.GUIDED_ANALYSIS),
        ("我想比较不同产品的销售额", EnhancedChatIntent.GUIDED_ANALYSIS),
        ("分析用户行为相关性", EnhancedChatIntent.GUIDED_ANALYSIS),
        
        # 探索性分析
        ("探索数据中隐藏的模式", EnhancedChatIntent.EXPLORATORY_ANALYSIS),
        ("自动生成数据洞察", EnhancedChatIntent.EXPLORATORY_ANALYSIS),
        ("建议一些有趣的分析方向", EnhancedChatIntent.EXPLORATORY_ANALYSIS),
        
        # 复用工件
        ("显示之前的报告", EnhancedChatIntent.REUSE_ARTIFACT),
        ("查看上次的可视化图表", EnhancedChatIntent.REUSE_ARTIFACT),
        ("重新打开那个分析结果", EnhancedChatIntent.REUSE_ARTIFACT),
        
        # 数据查询
        ("数据集有多少行", EnhancedChatIntent.DATA_INQUIRY),
        ("sales.csv文件的信息", EnhancedChatIntent.DATA_INQUIRY),
        ("查看price列的统计信息", EnhancedChatIntent.DATA_INQUIRY),
        
        # 技术支持
        ("遇到错误怎么办", EnhancedChatIntent.TECHNICAL_SUPPORT),
        ("如何安装这个工具", EnhancedChatIntent.TECHNICAL_SUPPORT),
        ("help me debug this issue", EnhancedChatIntent.TECHNICAL_SUPPORT),
        
        # 反馈投诉
        ("这个功能太慢了", EnhancedChatIntent.FEEDBACK_COMPLAINT),
        ("结果不准确", EnhancedChatIntent.FEEDBACK_COMPLAINT),
        ("需要改进用户体验", EnhancedChatIntent.FEEDBACK_COMPLAINT),
        
        # 一般聊天
        ("你好", EnhancedChatIntent.CHAT_ONLY),
        ("今天天气怎么样", EnhancedChatIntent.CHAT_ONLY),
        ("谢谢你的帮助", EnhancedChatIntent.CHAT_ONLY),
    ]
    
    recognizer = get_intent_recognizer()
    passed = 0
    total = len(test_cases)
    
    for message, expected_intent in test_cases:
        decision = recognizer.classify_intent(message)
        status = "✓" if decision.intent == expected_intent else "✗"
        confidence_indicator = "★" * int(decision.confidence * 5)
        
        print(f"{status} '{message}'")
        print(f"   意图: {decision.intent.value} (期望: {expected_intent.value})")
        print(f"   置信度: {decision.confidence:.2f} {confidence_indicator}")
        print(f"   理由: {decision.reason}")
        if decision.detected_entities:
            print(f"   实体: {decision.detected_entities}")
        print()
        
        if decision.intent == expected_intent:
            passed += 1
    
    print(f"通过率: {passed}/{total} ({passed/total*100:.1f}%)")


def test_entity_extraction():
    """测试实体提取功能"""
    print("=== 实体提取测试 ===")
    
    test_messages = [
        "分析 sales_data.csv 文件中 price 和 quantity 列的关系",
        "数据集有 1000 行记录",
        "查看 revenue.xlsx 和 cost.json 文件",
        "customer_id 字段的分布情况如何"
    ]
    
    recognizer = get_intent_recognizer()
    
    for message in test_messages:
        decision = recognizer.classify_intent(message)
        print(f"消息: '{message}'")
        print(f"检测到的实体: {decision.detected_entities}")
        print()


def test_confidence_calculation():
    """测试置信度计算"""
    print("=== 置信度计算测试 ===")
    
    test_messages = [
        "分析",  # 很短的消息
        "请详细分析这份数据的趋势和模式，包括统计信息和可视化",  # 较长的消息
        "我不知道该怎么做，请帮我分析一下",  # 模糊的消息
        "analyze the trend of sales data and generate insights",  # 英文消息
    ]
    
    recognizer = get_intent_recognizer()
    
    for message in test_messages:
        decision = recognizer.classify_intent(message)
        print(f"消息: '{message}'")
        print(f"长度: {len(message)} 字符")
        print(f"意图: {decision.intent.value}")
        print(f"置信度: {decision.confidence:.3f}")
        print(f"理由: {decision.reason}")
        print("-" * 50)


def demonstrate_migration_examples():
    """演示如何从旧系统迁移到新系统"""
    print("=== 迁移示例 ===")
    
    # 旧系统的使用方式
    print("旧系统使用方式:")
    print("""
    from orchestration.intent_router import classify_intent
    
    decision = classify_intent("分析数据", manifest)
    if decision.intent == ChatIntent.GUIDED_ANALYSIS:
        # 处理指导式分析
        pass
    """)
    
    print("\n新系统使用方式:")
    print("""
    from orchestration.enhanced_intent_router import enhanced_classify_intent
    
    decision = enhanced_classify_intent("分析数据", manifest)
    print(f"意图: {decision.intent.value}")
    print(f"置信度: {decision.confidence:.2f}")
    if decision.detected_entities:
        print(f"检测到实体: {decision.detected_entities}")
    """)
    
    # 实际演示
    print("\n实际演示:")
    message = "请分析 sales.csv 文件中 price 列的趋势"
    old_decision = classify_intent_simple(message)  # 模拟旧系统
    new_decision = enhanced_classify_intent(message)
    
    print(f"消息: '{message}'")
    print(f"旧系统结果: {old_decision['intent']} (置信度: N/A)")
    print(f"新系统结果: {new_decision.intent.value} (置信度: {new_decision.confidence:.2f})")
    if new_decision.detected_entities:
        print(f"新系统额外信息: 检测到 {new_decision.detected_entities}")


def classify_intent_simple(message: str) -> dict:
    """模拟旧系统的简单分类（用于对比）"""
    text = message.lower()
    if any(word in text for word in ['analyze', '分析', 'trend', '趋势']):
        return {'intent': 'guided_docs_analysis'}
    elif any(word in text for word in ['show', '显示', 'report', '报告']):
        return {'intent': 'reuse_artifact'}
    else:
        return {'intent': 'chat_only'}


if __name__ == "__main__":
    print("DeepAnalyze 增强意图识别系统测试")
    print("=" * 60)
    
    test_basic_classification()
    test_entity_extraction()
    test_confidence_calculation()
    demonstrate_migration_data_examples()
    
    print("\n测试完成！")