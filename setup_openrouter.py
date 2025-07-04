#!/usr/bin/env python3
"""配置OpenRouter作为MiniMax API的替代方案"""

import os
from pathlib import Path

def setup_openrouter():
    """设置OpenRouter配置"""
    print("🔧 配置OpenRouter作为MiniMax API替代方案")
    print("=" * 50)
    
    # OpenRouter配置说明
    print("\n📋 配置步骤：")
    print("1. 访问 https://openrouter.ai/")
    print("2. 注册账户并获取API Key")
    print("3. 运行以下命令设置环境变量：")
    print()
    
    # 提供配置命令
    print("💻 环境变量配置：")
    print("export OPENROUTER_API_KEY='your_openrouter_api_key_here'")
    print("export OPENROUTER_MODEL_NAME='minimax/minimax-01'")
    print()
    
    # 或者可以配置到TOML文件
    config_path = Path.home() / ".minimax_tagger.toml"
    print(f"📝 或者编辑配置文件: {config_path}")
    print("""
[api]
key = "your_openrouter_api_key_here"
base_url = "https://openrouter.ai/api/v1/chat/completions"
model_name = "minimax/minimax-01"
""")
    
    print("🎯 OpenRouter优势：")
    print("- 统一的API接口")
    print("- 更好的错误处理")
    print("- 支持多个模型提供商")
    print("- 降低直接调用MiniMax API的复杂性")
    print("- 按使用量付费，无需企业账户")
    
    print("\n✅ 配置完成后重新运行测试")

if __name__ == "__main__":
    setup_openrouter() 