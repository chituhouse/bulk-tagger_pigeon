#!/usr/bin/env python3
"""
MiniMax Tagger 功能演示脚本
测试上传和审阅功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from minimax_tagger.config import settings
from minimax_tagger.manifest import ManifestManager, create_manifest_from_directory
from minimax_tagger.pipeline import scan_images_in_directory, process_images_pipeline
from minimax_tagger.utils.logger import get_logger, setup_logger

logger = get_logger(__name__)

async def demo_upload_and_review():
    """演示上传和审阅功能"""
    
    print("🚀 MiniMax Tagger 功能演示")
    print("=" * 50)
    
    # 设置日志
    setup_logger(level="INFO")
    
    # 1. 扫描测试图片目录
    test_dir = Path("test_images")
    if not test_dir.exists():
        print("❌ 测试图片目录不存在")
        return False
    
    print(f"📁 扫描图片目录: {test_dir}")
    image_paths = scan_images_in_directory(test_dir)
    print(f"🖼️  发现图片: {len(image_paths)} 张")
    
    for img_path in image_paths:
        print(f"   - {img_path.name}")
    
    # 2. 创建或加载Manifest
    manifest_path = test_dir / "manifest.csv"
    
    if manifest_path.exists():
        print(f"\n📋 加载现有manifest: {manifest_path}")
        manifest_manager = ManifestManager(manifest_path)
        manifest_manager.load_from_csv()
        print(f"📊 已有记录: {len(manifest_manager.records)} 条")
    else:
        print(f"\n📋 创建新manifest: {manifest_path}")
        manifest_manager = create_manifest_from_directory(
            directory=test_dir,
            manifest_path=manifest_path
        )
        print(f"📊 新建记录: {len(manifest_manager.records)} 条")
    
    # 3. 显示当前状态
    pending_records = manifest_manager.get_pending_records()
    print(f"\n📋 处理状态:")
    print(f"   待处理: {len(pending_records)} 张")
    print(f"   已完成: {len(manifest_manager.records) - len(pending_records)} 张")
    
    # 4. 模拟API处理（如果有API配置）
    if settings.api_key and len(pending_records) > 0:
        print(f"\n🔄 开始处理图片...")
        
        try:
            # 使用测试提示词
            test_prompt = "请为这张图片生成详细的英文提示词，描述图片中的内容、颜色、风格等特征。"
            
            # 处理待处理的图片
            results = await process_images_pipeline(
                image_paths=[Path(record.filepath) for record in pending_records],
                prompt_template=test_prompt,
                progress_callback=lambda current, total: print(f"进度: {current}/{total}")
            )
            
            print(f"✅ 处理完成: {len(results)} 张图片")
            
            # 显示结果
            for img_path, prompt, success in results:
                status = "✅" if success else "❌"
                print(f"{status} {Path(img_path).name}: {prompt[:100]}...")
                
        except Exception as e:
            print(f"⚠️ API处理失败: {e}")
            print("这是正常的，因为需要有效的API配置")
    
    else:
        print(f"\n⚠️ 跳过API处理（未配置API或无待处理图片）")
    
    # 5. 演示审阅功能
    print(f"\n🔍 审阅功能演示:")
    
    all_records = manifest_manager.records
    if all_records:
        print(f"📝 可用的记录:")
        for i, record in enumerate(all_records[:3]):  # 只显示前3个
            print(f"   {i+1}. {record.filepath}")
            print(f"      状态: {record.status.value}")
            if record.prompt_en:
                print(f"      提示词: {record.prompt_en[:80]}...")
            print()
        
        # 模拟审阅操作
        if len(all_records) > 0:
            first_record = all_records[0]
            print(f"🎯 演示审阅操作 - 处理: {first_record.filepath}")
            
            # 模拟用户审阅
            print("   可用操作:")
            print("   1. ✅ 通过 (approved)")
            print("   2. ❌ 拒绝 (rejected)")
            print("   3. 🔄 重新生成 (pending)")
            print("   4. ✏️ 手工编辑提示词")
            
            # 这里可以添加实际的用户交互
            print("   (演示模式：自动设置为通过状态)")
            
            # 更新状态
            from minimax_tagger.manifest import ProcessStatus
            manifest_manager.update_record_status(first_record.filepath, ProcessStatus.APPROVED)
            manifest_manager.save_to_csv()
            
            print(f"   ✅ 已更新状态为: approved")
    
    # 6. 导出功能演示
    print(f"\n📤 导出功能演示:")
    
    try:
        exported_count = manifest_manager.export_to_txt_files()
        print(f"✅ 成功导出 {exported_count} 个TXT文件")
        
        # 显示导出的文件
        for record in manifest_manager.get_approved_records():
            txt_path = Path(record.filepath).with_suffix('.txt')
            if txt_path.exists():
                print(f"   📄 {txt_path}")
                
    except Exception as e:
        print(f"⚠️ 导出失败: {e}")
    
    print(f"\n🎉 演示完成！")
    print(f"💡 您可以:")
    print(f"   1. 查看 {manifest_path} 了解处理结果")
    print(f"   2. 检查生成的 .txt 文件")
    print(f"   3. 使用 GUI 界面进行可视化审阅")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(demo_upload_and_review())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print(f"\n👋 演示被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"❌ 演示过程出错: {e}")
        sys.exit(1) 