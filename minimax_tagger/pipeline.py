"""批处理管道和动态切块算法实现。"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Generator, List, Optional, Tuple

from .config import settings
from .utils.logger import get_logger
from .utils.image_io import validate_image_file, estimate_base64_size
from .utils.concurrency import run_tasks_with_limit

logger = get_logger(__name__)


def scan_images_in_directory(directory: Path, skip_invalid: bool = True) -> List[Path]:
    """
    递归扫描目录中的所有支持的图片文件。
    
    Args:
        directory: 要扫描的目录路径
        skip_invalid: 是否跳过无效的图片文件
    
    Returns:
        图片文件路径列表
    """
    if not directory.exists():
        logger.error(f"目录不存在: {directory}")
        return []
    
    if not directory.is_dir():
        logger.error(f"路径不是目录: {directory}")
        return []
    
    image_files = []
    invalid_count = 0
    
    for ext in settings.supported_extensions:
        # 递归查找各种格式的图片
        for pattern in [f"**/*{ext}", f"**/*{ext.upper()}"]:
            for image_path in directory.glob(pattern):
                # 验证图片文件
                if skip_invalid and not validate_image_file(image_path):
                    invalid_count += 1
                    logger.debug(f"跳过无效图片文件: {image_path}")
                    continue
                
                image_files.append(image_path)
    
    # 去重并排序
    image_files = sorted(set(image_files))
    
    logger.info(f"扫描目录 {directory}：找到 {len(image_files)} 个有效图片文件")
    if invalid_count > 0:
        logger.warning(f"跳过了 {invalid_count} 个无效图片文件")
    
    return image_files


# 移除了 calculate_image_size 函数，现在使用 utils.image_io 中的 estimate_base64_size


def dynamic_chunk_images(image_paths: List[Path]) -> Generator[List[Path], None, None]:
    """
    动态切块算法：根据文件大小将图片分组，确保每组的 base64 编码总大小不超过限制。
    
    Args:
        image_paths: 图片路径列表
    
    Yields:
        每个批次的图片路径列表
    """
    if not image_paths:
        return
    
    max_bytes = settings.max_batch_size_bytes
    current_batch = []
    current_size = 0
    
    # 基础 JSON 结构的开销（估算）
    base_overhead = 2048  # 约 2KB 的 JSON 结构开销
    
    for image_path in image_paths:
        try:
            # 计算这张图片编码后的大小
            image_size = estimate_base64_size(image_path)
            
            # 检查单张图片是否超过限制
            if image_size + base_overhead > max_bytes:
                logger.warning(f"图片太大，跳过处理: {image_path} ({image_size} bytes)")
                continue
            
            # 如果加入这张图片会超过限制，先处理当前批次
            if current_batch and (current_size + image_size + base_overhead > max_bytes):
                logger.debug(f"批次已满，切换到下一批次。当前批次大小: {current_size} bytes，图片数量: {len(current_batch)}")
                yield current_batch
                current_batch = []
                current_size = 0
            
            # 将图片加入当前批次
            current_batch.append(image_path)
            current_size += image_size
            
        except OSError as e:
            logger.warning(f"无法访问图片文件 {image_path}: {e}")
            continue
    
    # 处理最后一个批次
    if current_batch:
        yield current_batch


async def process_image_batch(
    image_paths: List[Path],
    prompt_template: str,
    system_prompt: Optional[str] = None
) -> List[Tuple[Path, str, bool]]:
    """
    处理一个图片批次。
    
    Args:
        image_paths: 图片路径列表
        prompt_template: 提示词模板
        system_prompt: 系统提示词
    
    Returns:
        结果列表：(图片路径, 生成的提示词, 是否成功)
    """
    from .api import call_minimax_vision, extract_prompt_from_response
    
    results = []
    
    try:
        # 调用 API
        api_response = await call_minimax_vision(
            prompt=prompt_template,
            image_paths=image_paths,
            system_prompt=system_prompt
        )
        
        # 提取生成的提示词
        generated_prompt = await extract_prompt_from_response(api_response)
        
        # 如果批次包含多张图片，需要分割结果
        if len(image_paths) == 1:
            results.append((image_paths[0], generated_prompt, True))
        else:
            # 对于多图批次，暂时为每张图片返回相同的提示词
            # TODO: 实现更智能的多图结果分割
            for image_path in image_paths:
                results.append((image_path, generated_prompt, True))
        
    except Exception as e:
        # 处理失败的情况
        error_msg = f"API 调用失败: {str(e)}"
        for image_path in image_paths:
            results.append((image_path, error_msg, False))
    
    return results


async def process_images_pipeline(
    image_paths: List[Path],
    prompt_template: str,
    system_prompt: Optional[str] = None,
    progress_callback=None
) -> List[Tuple[Path, str, bool]]:
    """
    完整的图片处理管道。
    
    Args:
        image_paths: 图片路径列表
        prompt_template: 提示词模板
        system_prompt: 系统提示词
        progress_callback: 进度回调函数
    
    Returns:
        所有结果列表：(图片路径, 生成的提示词, 是否成功)
    """
    if not image_paths:
        logger.warning("没有提供图片路径")
        return []
    
    logger.info(f"开始处理管道：{len(image_paths)} 张图片")
    
    all_results = []
    batches = list(dynamic_chunk_images(image_paths))
    total_batches = len(batches)
    
    logger.info(f"图片已分为 {total_batches} 个批次")
    
    # 创建批次处理任务
    async def process_single_batch(batch):
        try:
            return await process_image_batch(batch, prompt_template, system_prompt)
        except Exception as e:
            logger.error(f"批次处理失败: {e}")
            # 返回失败结果
            return [(img_path, f"批次处理失败: {e}", False) for img_path in batch]
    
    # 并发执行所有批次
    def progress_wrapper(completed: int, total: int):
        if progress_callback:
            progress_callback(completed, total)
        logger.info(f"处理进度: {completed}/{total} 批次")
    
    # 使用信号量控制并发
    semaphore = asyncio.Semaphore(settings.concurrency)
    
    async def execute_batch_with_limit(batch):
        async with semaphore:
            return await process_single_batch(batch)
    
    # 创建限制并发的批次任务
    limited_tasks = [execute_batch_with_limit(batch) for batch in batches]
    
    # 执行所有批次
    batch_results = await asyncio.gather(*limited_tasks, return_exceptions=True)
    
    # 整合所有结果，处理异常
    completed_batches = 0
    for i, batch_result in enumerate(batch_results):
        completed_batches += 1
        progress_wrapper(completed_batches, total_batches)
        
        if isinstance(batch_result, Exception):
            logger.error(f"批次 {i+1} 执行失败: {batch_result}")
            # 为失败的批次创建错误结果
            error_results = [(img_path, f"批次处理失败: {batch_result}", False) for img_path in batches[i]]
            all_results.extend(error_results)
        elif batch_result and isinstance(batch_result, list):
            all_results.extend(batch_result)
    
    logger.info(f"管道处理完成：成功处理 {len(all_results)} 个结果")
    return all_results


# 向后兼容性别名 - 为GUI提供process_images_batch函数
async def process_images_batch(
    image_paths: List[Path],
    prompt_template: str,
    system_prompt: Optional[str] = None,
    progress_callback=None
) -> List[Tuple[Path, str, bool]]:
    """
    向后兼容性别名：批量处理图片函数。
    
    实际调用 process_images_pipeline 函数。
    """
    return await process_images_pipeline(
        image_paths=image_paths,
        prompt_template=prompt_template,
        system_prompt=system_prompt,
        progress_callback=progress_callback
    ) 