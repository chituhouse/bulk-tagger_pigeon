#!/usr/bin/env python3
"""完整工作流程测试脚本"""

import os
import sys
from pathlib import Path

# 添加当前目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)

def test_gui_workflow():
    """测试完整的GUI工作流程"""
    try:
        print_section("启动GUI工作流程测试")
        
        # 创建测试环境
        test_dir = project_root / "test_workflow"
        test_dir.mkdir(exist_ok=True)
        
        # 复制一些测试图片到新文件夹
        test_images_dir = project_root / "test_images"
        if test_images_dir.exists():
            import shutil
            for img_file in test_images_dir.glob("*.{jpg,png,jpeg}"):
                shutil.copy2(img_file, test_dir)
                print(f"📁 复制测试图片: {img_file.name}")
        
        print(f"📂 测试文件夹路径: {test_dir}")
        print(f"📋 包含图片文件: {list(test_dir.glob('*.{jpg,png,jpeg}'))}")
        
        # 启动GUI
        print_section("启动GUI界面")
        print("🚀 启动MiniMax Tagger GUI...")
        print("📌 完整工作流程测试:")
        print("   1. 在'图片文件夹'中输入或选择:", test_dir)
        print("   2. 点击'创建Manifest'按钮")
        print("   3. 查看是否成功创建manifest.csv文件")
        print("   4. 输入测试API Key（可选）")
        print("   5. 点击'批量处理图片'按钮测试")
        print("   6. 使用图片审阅功能")
        print("")
        
        # 导入并启动GUI
        from minimax_tagger.gui import run_gui
        run_gui()
        
    except KeyboardInterrupt:
        print("\n👋 用户取消测试")
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()

def print_workflow_instructions():
    """打印工作流程说明"""
    print_section("MiniMax Tagger 完整工作流程")
    print("""
🎯 完整使用流程:

1️⃣ 准备图片文件夹
   - 将要处理的图片放在一个文件夹中
   - 支持的格式: .jpg, .jpeg, .png, .webp

2️⃣ 创建Manifest文件
   - 选择图片文件夹
   - 点击'创建Manifest'按钮
   - 系统会自动扫描图片并创建manifest.csv

3️⃣ 配置API信息
   - 输入MiniMax API Key
   - 可选：输入Group ID
   - 点击'保存配置'

4️⃣ 批量处理图片
   - 点击'批量处理图片'按钮
   - 系统会调用API为每张图片生成提示词

5️⃣ 审阅和编辑
   - 在右侧图片列表中选择图片
   - 查看生成的提示词
   - 可以通过/拒绝/重新生成

6️⃣ 导出结果
   - 点击'导出TXT'按钮
   - 为每张通过的图片生成同名.txt文件

💡 新功能亮点:
   ✅ 文件夹选择和自动扫描
   ✅ 一键创建Manifest文件
   ✅ 批量处理功能
   ✅ 图片审阅和状态管理
   ✅ 配置保存和加载
   ✅ 进度显示和错误处理
""")

if __name__ == "__main__":
    print_workflow_instructions()
    test_gui_workflow() 