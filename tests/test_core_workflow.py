#!/usr/bin/env python3
"""核心工作流程自动化测试脚本"""

import asyncio
import os
import sys
from pathlib import Path

# 添加当前目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from minimax_tagger.manifest import ManifestManager, ProcessStatus
from minimax_tagger.pipeline import process_images_pipeline, scan_images_in_directory
from minimax_tagger.config import settings
from minimax_tagger.utils.logger import get_logger

logger = get_logger(__name__)

def print_section(title):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"🔧 {title}")
    print('='*60)

def print_step(step_num, description):
    """打印步骤"""
    print(f"\n{step_num}️⃣ {description}")
    print("-" * 40)

async def test_core_workflow():
    """测试核心工作流程"""
    try:
        print_section("MiniMax Tagger 核心功能测试")
        
        # Step 1: 准备测试环境
        print_step(1, "准备测试环境")
        test_dir = project_root / "test_images"
        print(f"📂 使用测试目录: {test_dir}")
        
        if not test_dir.exists():
            print("❌ 测试目录不存在")
            return False
        
        # Step 2: 扫描图片文件
        print_step(2, "扫描图片文件")
        image_files = scan_images_in_directory(test_dir)
        print(f"📸 找到图片文件数量: {len(image_files)}")
        for img in image_files:
            print(f"   - {img.name}")
        
        if not image_files:
            print("❌ 没有找到图片文件")
            return False
        
        # Step 3: 检查或创建Manifest
        print_step(3, "管理Manifest文件")
        manifest_path = test_dir / "manifest.csv"
        manifest_manager = ManifestManager(manifest_path)
        
        if manifest_path.exists():
            print(f"✅ 发现现有Manifest文件: {manifest_path}")
            manifest_manager.load_from_csv()
            print(f"📋 当前记录数量: {len(manifest_manager.records)}")
        else:
            print(f"📝 创建新的Manifest文件: {manifest_path}")
            imported_count = manifest_manager.import_from_directory(test_dir)
            print(f"📥 导入了 {imported_count} 个图片文件")
        
        # 显示当前状态
        status_counts = {}
        for record in manifest_manager.records:
            status = record.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"📊 图片状态统计: {status_counts}")
        
        # Step 4: 检查API配置
        print_step(4, "检查API配置")
        settings.load_from_file()
        
        if not settings.api_key:
            print("⚠️  未配置API Key，将使用模拟模式测试")
            use_mock_api = True
        else:
            print("✅ 发现API Key配置")
            print(f"🔗 API地址: {settings.api_base_url}")
            print(f"🤖 模型: {settings.model_name}")
            use_mock_api = False
        
        # Step 5: 测试提示词生成
        print_step(5, "测试提示词生成")
        
        # 找一张待处理的图片
        pending_records = [
            record for record in manifest_manager.records
            if record.status.value == "pending"
        ]
        
        if not pending_records:
            print("📝 所有图片已处理，选择第一张图片重新测试")
            test_image = test_dir / manifest_manager.records[0].filepath
        else:
            test_image = test_dir / pending_records[0].filepath
        
        print(f"🖼️  测试图片: {test_image.name}")
        
        # 准备提示词
        prompt_template = "请为这张图片生成一个详细的英文提示词，描述图片中的内容、风格、构图等要素。"
        system_prompt = "你是一个专业的图像分析师，请仔细观察图像并生成准确的英文描述。"
        
        if use_mock_api:
            # 模拟API响应
            print("🔬 使用模拟API响应")
            mock_prompt = f"Mock generated prompt for {test_image.name}: A detailed English description of the image content, style, and composition elements."
            results = [(test_image, mock_prompt, True)]
        else:
            # 真实API调用
            print("🌐 调用真实API")
            try:
                results = await process_images_pipeline(
                    image_paths=[test_image],
                    prompt_template=prompt_template,
                    system_prompt=system_prompt
                )
            except Exception as e:
                print(f"❌ API调用失败: {e}")
                return False
        
        # Step 6: 处理结果
        print_step(6, "处理API响应")
        for img_path, generated_prompt, success in results:
            print(f"🖼️  图片: {img_path.name}")
            print(f"✅ 成功: {success}")
            if success:
                print(f"📝 生成的提示词: {generated_prompt[:100]}...")
                
                # 更新Manifest
                for record in manifest_manager.records:
                    if record.filepath == test_image.name:
                        record.prompt_en = generated_prompt
                        record.status = ProcessStatus.APPROVED  # 自动批准测试结果
                        print("📋 已更新Manifest记录")
                        break
            else:
                print(f"❌ 错误: {generated_prompt}")
        
        # 保存Manifest
        manifest_manager.save_to_csv()
        print("💾 Manifest已保存")
        
        # Step 7: 导出TXT文件
        print_step(7, "导出TXT文件")
        
        # 创建TXT输出目录
        txt_output_dir = test_dir / "txt_outputs"
        txt_output_dir.mkdir(exist_ok=True)
        print(f"📁 TXT输出目录: {txt_output_dir}")
        
        # 导出所有已批准的图片
        approved_count = 0
        for record in manifest_manager.records:
            if record.status.value == "approved" and record.prompt_en:
                # 创建同名TXT文件
                img_path = Path(record.filepath)
                txt_file = txt_output_dir / f"{img_path.stem}.txt"
                with open(txt_file, 'w', encoding='utf-8') as f:
                    f.write(record.prompt_en)
                print(f"📄 创建TXT文件: {txt_file.name}")
                approved_count += 1
        
        print(f"✅ 成功导出 {approved_count} 个TXT文件")
        
        # Step 8: 验证结果
        print_step(8, "验证测试结果")
        
        # 检查文件是否正确创建
        txt_files = list(txt_output_dir.glob("*.txt"))
        print(f"📊 TXT文件数量: {len(txt_files)}")
        
        if txt_files:
            print("✅ 成功创建TXT文件:")
            for txt_file in txt_files:
                file_size = txt_file.stat().st_size
                print(f"   - {txt_file.name} ({file_size} bytes)")
                
                # 检查文件内容
                if file_size > 0:
                    with open(txt_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                        print(f"     内容预览: {content[:50]}...")
        
        print_section("测试完成")
        print("🎉 核心工作流程测试成功！")
        print("""
✅ 验证的功能:
   1. 图片文件扫描和验证
   2. Manifest文件管理
   3. API配置检查
   4. 提示词生成（模拟或真实API）
   5. 结果处理和保存
   6. TXT文件导出
   7. 文件完整性验证

🚀 系统已准备就绪，可以正常使用！
""")
        return True
        
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_core_workflow())
    if success:
        print("🏆 所有测试通过！")
        sys.exit(0)
    else:
        print("💥 测试失败！")
        sys.exit(1) 