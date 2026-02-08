"""
调试增强意图识别系统的正则表达式匹配
"""

import re

def debug_patterns():
    """调试正则表达式模式"""
    
    # 测试消息
    test_message = "请分析这份销售数据的趋势"
    print(f"测试消息: '{test_message}'")
    print(f"小写化: '{test_message.lower()}'")
    print()
    
    # 测试各种正则表达式模式
    patterns = [
        r'\b(analyze|分析)\b',
        r'(?:^|\s)(?:analyze|分析)(?:\s|$)',
        r'analyze|分析',
        r'.*(analyze|分析).*',
    ]
    
    for i, pattern in enumerate(patterns, 1):
        print(f"模式 {i}: {pattern}")
        match = re.search(pattern, test_message.lower())
        print(f"  匹配结果: {match is not None}")
        if match:
            print(f"  匹配内容: '{match.group()}'")
        print()
    
    # 测试关键词匹配
    print("=== 关键词直接匹配测试 ===")
    keywords = ['analyze', '分析', 'trend', '趋势']
    text = test_message.lower()
    
    for keyword in keywords:
        found = keyword in text
        print(f"'{keyword}' in text: {found}")
    
    # 测试中文分词
    print("\n=== 中文分词测试 ===")
    import jieba
    try:
        words = list(jieba.cut(test_message))
        print(f"分词结果: {words}")
        for word in words:
            if word in ['分析', '趋势']:
                print(f"找到关键词: {word}")
    except ImportError:
        print("jieba未安装，跳过分词测试")

if __name__ == "__main__":
    debug_patterns()