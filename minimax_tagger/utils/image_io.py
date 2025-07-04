"""图片处理工具 - Base64 编码、压缩等。"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Tuple, Optional

from .logger import get_logger

logger = get_logger(__name__)


def encode_image_to_base64(image_path: Path) -> str:
    """将图片文件编码为 base64 字符串。
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        base64 编码的字符串
        
    Raises:
        FileNotFoundError: 文件不存在
        IOError: 文件读取错误
    """
    if not image_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    if not image_path.is_file():
        raise ValueError(f"路径不是文件: {image_path}")
    
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()
        
        if len(image_data) == 0:
            raise ValueError(f"图片文件为空: {image_path}")
        
        encoded = base64.b64encode(image_data).decode("utf-8")
        logger.debug(f"成功编码图片: {image_path} ({len(image_data)} bytes -> {len(encoded)} chars)")
        return encoded
        
    except Exception as e:
        logger.error(f"编码图片失败 {image_path}: {e}")
        raise IOError(f"读取图片文件失败: {e}") from e


def get_image_info(image_path: Path) -> Tuple[str, int]:
    """获取图片信息
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        (MIME类型, 文件大小)
        
    Raises:
        ValueError: 不支持的图片格式
    """
    if not image_path.exists():
        raise FileNotFoundError(f"图片文件不存在: {image_path}")
    
    suffix = image_path.suffix.lower()
    
    # 支持的格式映射
    mime_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg", 
        ".png": "image/png",
        ".webp": "image/webp"
    }
    
    if suffix not in mime_types:
        raise ValueError(f"不支持的图片格式: {suffix}")
    
    file_size = image_path.stat().st_size
    return mime_types[suffix], file_size


def estimate_base64_size(image_path: Path) -> int:
    """估算图片 base64 编码后的大小
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        估算的 base64 编码大小（字节）
    """
    try:
        file_size = image_path.stat().st_size
        # Base64 编码会增加约 33% 的大小，再加一些额外开销
        return int(file_size * 1.33) + 1024
    except OSError:
        logger.warning(f"无法获取文件大小: {image_path}")
        return 0


def validate_image_file(image_path: Path) -> bool:
    """验证图片文件是否有效
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        是否为有效的图片文件
    """
    try:
        # 检查文件存在性
        if not image_path.exists() or not image_path.is_file():
            return False
        
        # 检查文件扩展名
        _, _ = get_image_info(image_path)
        
        # 检查文件不为空
        if image_path.stat().st_size == 0:
            return False
        
        return True
        
    except Exception as e:
        logger.debug(f"图片文件验证失败 {image_path}: {e}")
        return False


def create_image_data_url(image_path: Path) -> str:
    """创建图片的 data URL
    
    Args:
        image_path: 图片文件路径
        
    Returns:
        完整的 data URL 字符串
    """
    mime_type, _ = get_image_info(image_path)
    base64_data = encode_image_to_base64(image_path)
    return f"data:{mime_type};base64,{base64_data}" 