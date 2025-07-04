#!/usr/bin/env python3
"""
TXT导出功能测试
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from minimax_tagger.manifest import ManifestManager

def test_txt_export():
    """测试TXT导出功能"""
    
    print("📤 测试TXT文件导出功能")
    print("=" * 40)
    
    # 加载manifest
    manifest_path = Path("test_images/manifest.csv")
    if not manifest_path.exists():
        print("❌ manifest文件不存在")
        return False
    
    manager = ManifestManager(manifest_path)
    manager.load_from_csv()
    
    print(f"📋 已加载 {len(manager.records)} 条记录")
    
    # 显示状态
    approved_records = manager.get_approved_records()
    pending_records = manager.get_pending_records()
    
    print(f"✅ 已通过: {len(approved_records)} 条")
    print(f"⏳ 待处理: {len(pending_records)} 条")
    
    if not approved_records:
        print("⚠️ 没有已通过的记录，无法导出TXT文件")
        return False
    
    # 执行导出
    try:
        exported_count = manager.export_to_txt_files()
        print(f"🎉 成功导出 {exported_count} 个TXT文件")
        
        # 验证导出的文件
        print("\n📄 导出文件验证:")
        for record in approved_records:
            image_path = Path("test_images") / record.filepath
            txt_path = image_path.with_suffix('.txt')
            
            if txt_path.exists():
                content = txt_path.read_text(encoding='utf-8')
                print(f"✅ {txt_path.name}: {len(content)} 字符")
                print(f"   内容预览: {content[:80]}...")
            else:
                print(f"❌ {txt_path.name}: 文件不存在")
        
        return True
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        return False

if __name__ == "__main__":
    success = test_txt_export()
    sys.exit(0 if success else 1) 