"""日志工具模块 - 统一的日志配置。"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

try:
    from loguru import logger
except ImportError:
    # 如果没有安装 loguru，使用标准库
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)


def setup_logger(
    level: str = "INFO",
    log_file: Optional[Path] = None,
    rotation: str = "10 MB",
    retention: str = "7 days"
) -> None:
    """设置日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径，None 则只输出到控制台
        rotation: 日志轮转大小
        retention: 日志保留时间
    """
    if "loguru" in sys.modules:
        # 移除默认的 handler
        logger.remove()
        
        # 添加控制台输出
        logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                   "<level>{message}</level>"
        )
        
        # 添加文件输出（如果指定了文件）
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            logger.add(
                log_file,
                level=level,
                rotation=rotation,
                retention=retention,
                format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
                encoding="utf-8"
            )


def get_logger(name: str = __name__):
    """获取 logger 实例"""
    if "loguru" in sys.modules:
        return logger.bind(name=name)
    else:
        return logging.getLogger(name)


# 默认设置
setup_logger(level="INFO") 