#!/usr/bin/env python3
"""MiniMax Tagger 完整工作流程演示"""

import sys
import shutil
from pathlib import Path

# 添加当前目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def print_header(title):
    """打印标题"""
    print(f"\n{'='*60}")
    print(f"🎯 {title}")
    print('='*60)

def print_step(step, description):
    """打印步骤"""
    print(f"\n{step} {description}")
    print("-" * 50)

def create_demo_environment():
    """创建演示环境"""
    print_header("MiniMax Tagger 完整工作流程演示")
    
    # 创建演示文件夹
    demo_dir = project_root / "demo_images"
    demo_dir.mkdir(exist_ok=True)
    
    # 复制测试图片到演示文件夹
    test_images_dir = project_root / "test_images"
    if test_images_dir.exists():
        for img_file in test_images_dir.glob("*.{jpg,png,jpeg}"):
            if img_file.name != "manifest.csv":  # 不复制manifest文件
                dest_file = demo_dir / img_file.name
                if not dest_file.exists():
                    shutil.copy2(img_file, dest_file)
                    print(f"📸 复制演示图片: {img_file.name}")
    
    print(f"📁 演示环境路径: {demo_dir}")
    return demo_dir

def show_workflow_steps():
    """显示完整工作流程步骤"""
    print_header("完整工作流程步骤")
    
    steps = [
        "1️⃣ 准备图片文件夹 - 将要处理的图片放在一个文件夹中",
        "2️⃣ 启动GUI界面 - 运行 python gui_test.py",
        "3️⃣ 选择图片文件夹 - 点击'浏览文件夹'按钮",
        "4️⃣ 创建Manifest - 点击'创建Manifest'按钮扫描图片",
        "5️⃣ 配置API信息 - 输入MiniMax API Key和Group ID",
        "6️⃣ 批量处理图片 - 点击'批量处理图片'按钮",
        "7️⃣ 审阅生成结果 - 在右侧查看和编辑提示词",
        "8️⃣ 导出TXT文件 - 点击'导出TXT'按钮生成训练文件"
    ]
    
    for step in steps:
        print(step)
    
    print_header("功能特色")
    features = [
        "✅ 支持批量处理 - 一次处理多张图片",
        "✅ 智能切块算法 - 根据文件大小动态分组",
        "✅ 错误重试机制 - 自动处理API调用失败",
        "✅ 进度实时显示 - 查看处理进度和状态",
        "✅ 结果审阅功能 - 手动调整生成的提示词",
        "✅ 配置持久化 - API配置自动保存",
        "✅ 多格式支持 - 支持jpg、png、webp等格式",
        "✅ LoRA训练准备 - 自动生成配对的txt文件"
    ]
    
    for feature in features:
        print(feature)

def main():
    """主函数"""
    # 创建演示环境
    demo_dir = create_demo_environment()
    
    # 显示工作流程
    show_workflow_steps()
    
    print_header("开始演示")
    print(f"""
🚀 演示准备完成！

📂 演示文件夹: {demo_dir}
📋 包含图片: {list(demo_dir.glob('*.{jpg,png,jpeg}'))}

💡 接下来您可以：

方式1 - GUI界面演示:
   运行: python gui_test.py
   1. 在'图片文件夹'中输入: {demo_dir}
   2. 点击'创建Manifest'
   3. 输入API Key进行测试
   4. 体验完整功能

方式2 - 命令行演示:
   运行: python test_core_workflow.py
   自动测试所有核心功能

方式3 - 完整工作流程:
   运行: python test_complete_workflow.py
   启动GUI进行完整流程测试

🎯 推荐使用方式1进行交互式演示！
""")

if __name__ == "__main__":
    main() 