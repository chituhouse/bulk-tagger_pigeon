#!/usr/bin/env python3
"""
GUI 界面测试脚本
测试用户界面的上传和审阅功能
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from minimax_tagger.gui import MainWindow

def test_gui():
    """测试GUI界面"""
    
    print("🚀 启动 MiniMax Tagger GUI 测试")
    print("=" * 50)
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = MainWindow()
    
    # 显示窗口
    window.show()
    
    print("✅ GUI 已启动")
    print("💡 测试说明:")
    print("   1. 点击'浏览'按钮选择 test_images/manifest.csv")
    print("   2. 点击'加载'按钮加载数据")
    print("   3. 在左侧输入API Key（如果有的话）")
    print("   4. 查看右侧的图片列表和提示词")
    print("   5. 测试'保存配置'、'开始处理'、'导出TXT'等功能")
    print("   6. 关闭窗口退出测试")
    print()
    
    # 运行应用
    return app.exec()

if __name__ == "__main__":
    try:
        exit_code = test_gui()
        print(f"\n👋 GUI 测试完成，退出码: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"❌ GUI 测试出错: {e}")
        sys.exit(1) 