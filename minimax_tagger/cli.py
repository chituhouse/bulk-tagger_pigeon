"""MiniMax Tagger 命令行入口。"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from .config import settings
from .utils.logger import get_logger, setup_logger
from .pipeline import scan_images_in_directory, process_images_pipeline
from .manifest import ManifestManager, create_manifest_from_directory, ProcessStatus
from .api import call_minimax_vision

logger = get_logger(__name__)

async def check_config():
    """验证API配置是否正确"""
    logger.info("🔍 开始验证 MiniMax API 配置...")
    
    # 检查配置完整性
    if not settings.validate():
        logger.error("❌ 配置验证失败")
        return False
    
    # 显示当前配置
    logger.info(f"📋 当前配置:")
    logger.info(f"  API URL: {settings.api_base_url}")
    logger.info(f"  模型名称: {settings.model_name}")
    logger.info(f"  API Key: {settings.api_key[:10] + '...' + settings.api_key[-4:] if settings.api_key else 'None'}")
    logger.info(f"  Group ID: {settings.group_id or '未设置'}")
    logger.info(f"  并发数: {settings.concurrency}")
    logger.info(f"  重试次数: {settings.retry_max}")
    
    try:
        # 创建测试图片（1x1 像素的PNG）
        import base64
        test_image_data = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAGA7VT9mwAAAABJRU5ErkJggg=="
        test_image_path = Path("/tmp/test_minimax.png") if sys.platform != "win32" else Path("test_minimax.png")
        
        # 写入测试图片
        with open(test_image_path, "wb") as f:
            f.write(base64.b64decode(test_image_data))
        
        logger.info("🔄 测试API连接中...")
        
        # 调用API测试
        response = await call_minimax_vision(
            prompt="请描述这张图片",
            image_paths=[test_image_path],
            system_prompt="简单描述图片内容"
        )
        
        # 清理测试文件
        test_image_path.unlink(missing_ok=True)
        
        if response and "choices" in response:
            logger.info("✅ API 连接测试成功！")
            logger.info(f"📝 测试响应: {response['choices'][0]['message']['content'][:100]}...")
            return True
        else:
            logger.error("❌ API 响应格式异常")
            logger.error(f"响应内容: {response}")
            return False
            
    except Exception as e:
        # 清理测试文件
        if 'test_image_path' in locals():
            test_image_path.unlink(missing_ok=True)
            
        logger.error(f"❌ API 连接测试失败: {e}")
        logger.error("请检查:")
        logger.error("  1. API Key 是否正确")
        logger.error("  2. Group ID 是否需要（企业账号）")
        logger.error("  3. 网络连接是否正常")
        logger.error("  4. API 额度是否充足")
        return False

def validate_args(args):
    """验证命令行参数"""
    input_path = Path(args.input_path)
    
    # 验证输入路径
    if not input_path.exists():
        logger.error(f"输入路径不存在: {input_path}")
        return False
    
    # 验证并发数
    if args.concurrency < 1:
        logger.error("并发数必须大于 0")
        return False
    
    if args.concurrency > 10:
        logger.warning("并发数较高可能导致 API 限流，建议使用较小的值")
    
    # 验证重试次数
    if args.retry < 0:
        logger.error("重试次数不能为负数")
        return False
    
    # 验证提示词
    if not args.prompt.strip():
        logger.error("提示词不能为空")
        return False
    
    return True


async def run_processing(args):
    """运行处理流程"""
    input_path = Path(args.input_path)
    
    # 更新配置
    settings.concurrency = args.concurrency
    settings.retry_max = args.retry
    
    # 验证 API 配置
    if not settings.validate():
        logger.error("API 配置不完整，请设置环境变量")
        return False
    
    try:
        # 判断输入类型
        if input_path.is_file() and input_path.suffix.lower() == '.csv':
            # 处理现有 manifest
            manifest_manager = ManifestManager(input_path)
            manifest_manager.load_from_csv()
            
            # 获取待处理的图片
            pending_records = manifest_manager.get_pending_records()
            if not pending_records:
                logger.info("没有待处理的图片记录")
                return True
            
            image_paths = [Path(record.filepath) for record in pending_records]
            
        elif input_path.is_dir():
            # 扫描目录并创建 manifest
            manifest_path = input_path / "manifest.csv"
            
            if manifest_path.exists() and not args.force_recreate:
                # 加载现有 manifest
                manifest_manager = ManifestManager(manifest_path)
                manifest_manager.load_from_csv()
                
                # 导入新的图片文件
                imported_count = manifest_manager.import_from_directory(input_path)
                if imported_count > 0:
                    manifest_manager.save_to_csv()
                    logger.info(f"添加了 {imported_count} 个新的图片文件")
            else:
                # 创建新的 manifest
                manifest_manager = create_manifest_from_directory(input_path, manifest_path)
            
            # 获取待处理的图片
            pending_records = manifest_manager.get_pending_records()
            if not pending_records:
                logger.info("没有待处理的图片记录")
                return True
            
            # 转换为绝对路径
            image_paths = [input_path / record.filepath for record in pending_records]
            
        else:
            logger.error(f"不支持的输入类型: {input_path}")
            return False
        
        # 设置进度回调
        def progress_callback(current: int, total: int):
            percentage = (current / total) * 100 if total > 0 else 0
            logger.info(f"处理进度: {current}/{total} ({percentage:.1f}%)")
        
        # 执行处理
        logger.info(f"开始处理 {len(image_paths)} 张图片")
        results = await process_images_pipeline(
            image_paths,
            args.prompt,
            settings.system_prompt,
            progress_callback
        )
        
        # 更新 manifest
        success_count = 0
        for image_path, prompt_result, success in results:
            if success:
                # 转换为相对路径
                if input_path.is_dir():
                    relative_path = str(image_path.relative_to(input_path))
                else:
                    relative_path = str(image_path)
                
                manifest_manager.add_or_update_record(
                    filepath=relative_path,
                    prompt_en=prompt_result,
                    status=ProcessStatus.PENDING  # 等待人工审阅
                )
                success_count += 1
            else:
                logger.warning(f"处理失败: {image_path} - {prompt_result}")
        
        # 保存结果
        manifest_manager.save_to_csv()
        
        logger.info(f"处理完成：成功 {success_count}/{len(results)} 张图片")
        return True
        
    except KeyboardInterrupt:
        logger.info("用户中断处理")
        return False
    except Exception as e:
        logger.error(f"处理过程中发生错误: {e}")
        return False


def main():
    """主命令行入口函数"""
    parser = argparse.ArgumentParser(
        description="MiniMax Tagger - 批量反推提示词工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python -m minimax_tagger manifest.csv --prompt "英文反推提示词模板"
  python -m minimax_tagger data/ --prompt "模板" --concurrency 3 --retry 2
        """
    )
    
    parser.add_argument(
        "input_path", 
        nargs="?",
        help="输入路径：manifest CSV 文件或包含图片的目录"
    )
    parser.add_argument(
        "--prompt", 
        help="主提示词模板 (英文)"
    )
    parser.add_argument(
        "--check-config",
        action="store_true",
        help="验证API配置是否正确"
    )
    parser.add_argument(
        "--concurrency", 
        type=int, 
        default=1,
        help="并发协程数 (默认: 1)"
    )
    parser.add_argument(
        "--retry", 
        type=int, 
        default=3,
        help="失败重试次数上限 (默认: 3)"
    )
    parser.add_argument(
        "--skip-exist", 
        action="store_true",
        help="跳过已经处理过的图片"
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true", 
        help="强制重新创建 manifest 文件"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="日志级别 (默认: INFO)"
    )
    parser.add_argument(
        "--log-file",
        help="日志文件路径 (可选)"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    log_file = Path(args.log_file) if args.log_file else None
    setup_logger(level=args.log_level, log_file=log_file)
    
    logger.info("MiniMax Tagger v1.0.0 启动")
    
    # 尝试加载配置文件
    settings.load_from_file()
    
    # 配置验证模式
    if args.check_config:
        try:
            success = asyncio.run(check_config())
            sys.exit(0 if success else 1)
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            sys.exit(1)
    
    # 正常处理模式需要验证参数
    if not args.input_path:
        logger.error("错误：需要指定输入路径")
        parser.print_help()
        sys.exit(1)
    
    if not args.prompt:
        logger.error("错误：需要指定提示词")
        parser.print_help()
        sys.exit(1)
    
    logger.info(f"输入路径: {args.input_path}")
    logger.info(f"主提示词: {args.prompt}")
    logger.info(f"并发数: {args.concurrency}")
    logger.info(f"重试次数: {args.retry}")
    
    # 验证参数
    if not validate_args(args):
        sys.exit(1)
    
    # 运行处理流程
    try:
        success = asyncio.run(run_processing(args))
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 