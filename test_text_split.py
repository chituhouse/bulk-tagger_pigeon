#!/usr/bin/env python3
"""测试中英文分离功能"""

from minimax_tagger.utils.text_utils import split_chinese_english

def test_split_function():
    """测试中英文分离功能"""
    
    # 测试用例1：混合中英文
    test_text1 = """中文提示词：
这张图片展示了一位身穿传统中式服饰的人物。他的服饰主要由深红色和黑色组成，整体风格庄重典雅。

English prompt:
A person wearing traditional Chinese clothing. The outfit consists mainly of deep red and black colors, with an overall dignified and elegant style."""
    
    # 测试用例2：API返回的实际格式
    test_text2 = """提示词：

中文：
图片中的人物身穿古代官服，头戴精致的金色冠饰，整体造型庄重威严。

English:
The figure in the image wears ancient official robes with an exquisite golden crown, presenting a dignified and majestic appearance."""
    
    # 测试用例3：纯英文
    test_text3 = """A detailed portrait of a person in traditional dress
featuring red and black colors
dignified pose and elegant styling"""
    
    # 测试用例4：纯中文
    test_text4 = """一位身穿传统服饰的人物
服装以红色和黑色为主
姿态庄重优雅"""
    
    test_cases = [
        ("混合中英文", test_text1),
        ("API格式", test_text2), 
        ("纯英文", test_text3),
        ("纯中文", test_text4)
    ]
    
    for name, text in test_cases:
        print(f"\n=== 测试用例：{name} ===")
        print(f"原文：\n{text}")
        
        english, chinese = split_chinese_english(text)
        
        print(f"\n英文部分：\n{english}")
        print(f"\n中文部分：\n{chinese}")
        print("-" * 50)

if __name__ == "__main__":
    test_split_function() 