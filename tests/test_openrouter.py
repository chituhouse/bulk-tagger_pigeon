#!/usr/bin/env python3
"""
OpenRouter MiniMax测试脚本
"""

import asyncio
import aiohttp
import ssl
import os
import json
import base64
from pathlib import Path

async def test_openrouter_minimax():
    """测试OpenRouter的MiniMax-01模型"""
    
    # 使用您的OpenRouter API Key
    api_key = input("请输入您的OpenRouter API Key (或按回车跳过): ").strip()
    if not api_key:
        print("❌ 需要OpenRouter API Key才能测试")
        print("请访问 https://openrouter.ai 获取API Key")
        return False
    
    # 读取测试图片
    image_path = Path("test_images/test_shapes.png")
    if not image_path.exists():
        print(f"❌ 测试图片不存在: {image_path}")
        return False
    
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    base64_data = base64.b64encode(image_data).decode('utf-8')
    
    print(f"📊 图片信息:")
    print(f"   文件路径: {image_path}")
    print(f"   文件大小: {len(image_data)} bytes")
    print(f"   Base64大小: {len(base64_data)} chars")
    
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/minimax-tagger",
        "X-Title": "MiniMax Tagger Test"
    }
    
    payload = {
        "model": "minimax/minimax-01",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请为这张图片生成详细的英文提示词，描述图片中的颜色、形状和内容。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_data}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0.2,
        "max_tokens": 500  # 限制输出长度以减少费用
    }
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    
    try:
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=60)  # OpenRouter可能需要更长时间
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            print(f"\n🔄 发送请求到 OpenRouter...")
            print(f"   模型: minimax/minimax-01")
            print(f"   请求大小: {len(json.dumps(payload))} bytes")
            
            async with session.post(url, json=payload, headers=headers) as response:
                print(f"📊 响应状态码: {response.status}")
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        result = json.loads(response_text)
                        content = result["choices"][0]["message"]["content"]
                        print(f"✅ 成功!")
                        print(f"📝 AI回复:")
                        print(f"   {content}")
                        
                        # 检查是否真的理解了图片
                        vision_keywords = ["红色", "蓝色", "圆形", "矩形", "形状", "颜色", "red", "blue", "circle", "rectangle", "shape", "color"]
                        understood = any(keyword.lower() in content.lower() for keyword in vision_keywords)
                        
                        if understood:
                            print(f"🎉 模型成功理解了图片内容!")
                            return True
                        else:
                            print(f"⚠️  模型回复没有明确描述图片具体内容")
                            return False
                            
                    except Exception as e:
                        print(f"❌ 解析响应失败: {e}")
                        return False
                else:
                    try:
                        error_json = json.loads(response_text)
                        print(f"❌ 错误:")
                        print(json.dumps(error_json, indent=2, ensure_ascii=False))
                    except:
                        print(f"❌ 错误: {response_text[:500]}")
                    return False
                    
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

if __name__ == "__main__":
    print("OpenRouter MiniMax-01 图片理解测试")
    print("=" * 50)
    
    result = asyncio.run(test_openrouter_minimax())
    
    if result:
        print(f"\n🎉 OpenRouter方案可用!")
        print("您可以设置以下环境变量来使用:")
        print("export OPENROUTER_API_KEY='your_key_here'")
        print("然后正常运行程序即可。")
    else:
        print("\n❌ OpenRouter方案测试失败")
        print("请检查API Key或模型可用性") 