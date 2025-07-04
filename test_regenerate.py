#!/usr/bin/env python3
"""测试重新生成功能的核心逻辑"""

import sys
import asyncio
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "minimax_tagger"))

from minimax_tagger.manifest import ManifestManager, ProcessStatus
from minimax_tagger.pipeline import process_image_batch

async def test_regenerate():
    """测试重新生成功能"""
    print("🧪 开始测试重新生成功能...")
    
    # 检查测试图片
    test_image = Path("demo_images/test_image.jpg")
    if not test_image.exists():
        print(f"❌ 测试图片不存在: {test_image}")
        return
    
    print(f"✅ 找到测试图片: {test_image}")
    
    # 模拟重新生成过程
    try:
        print("🔄 开始调用API...")
        
        results = await process_image_batch(
            image_paths=[test_image],
            prompt_template="请为这张图片生成一个详细的英文提示词，描述图片中的内容、风格、构图等要素。",
            system_prompt="你是一个专业的图像分析师，请仔细观察图像并生成准确的英文描述。"
        )
        
        if results:
            image_path, prompt, success = results[0]
            print(f"✅ API调用成功")
            print(f"📸 图片: {image_path}")
            print(f"🎯 成功: {success}")
            print(f"📝 提示词: {prompt[:100]}...")
            
            # 测试TXT文件创建
            txt_path = test_image.with_suffix(".txt")
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            print(f"✅ 创建TXT文件: {txt_path}")
            
        else:
            print("❌ API返回空结果")
            
    except Exception as e:
        print(f"❌ API调用失败: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    print("🚀 重新生成功能测试")
    print("=" * 50)
    
    try:
        asyncio.run(test_regenerate())
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    main() 