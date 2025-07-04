"""MiniMax vision-02 API 调用封装。"""
from __future__ import annotations

import asyncio
import ssl
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import aiohttp
from .config import settings
from .utils.logger import get_logger
from .utils.image_io import create_image_data_url, validate_image_file
from .utils.concurrency import retry_async

logger = get_logger(__name__)


async def call_minimax_vision(
    prompt: str,
    image_paths: List[Path],
    system_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    调用 MiniMax vision-02 API 进行图像分析。
    
    Args:
        prompt: 用户提示词
        image_paths: 图片路径列表
        system_prompt: 系统提示词，可选
    
    Returns:
        API 响应结果
    
    Raises:
        aiohttp.ClientError: HTTP 请求错误
        ValueError: API 配置错误
    """
    if not settings.validate():
        raise ValueError("MiniMax API 配置不完整")
    
    # 构建消息内容
    messages = []
    
    # 添加系统消息（OpenRouter使用标准OpenAI格式）
    if system_prompt or settings.system_prompt:
        if settings.use_openrouter:
            # OpenRouter使用标准格式
            messages.append({
                "role": "system",
                "content": system_prompt or settings.system_prompt
            })
        else:
            # MiniMax原生格式
            messages.append({
                "role": "system",
                "content": [{"type": "text", "text": system_prompt or settings.system_prompt}]
            })
    
    # 构建用户消息内容
    user_content: List[Dict[str, Any]] = [{"type": "text", "text": prompt}]
    
    # 添加图片内容
    for image_path in image_paths:
        if not validate_image_file(image_path):
            raise ValueError(f"无效的图片文件: {image_path}")
        
        try:
            data_url = create_image_data_url(image_path)
            user_content.append({
                "type": "image_url",
                "image_url": {"url": data_url}
            })
            logger.debug(f"成功添加图片到请求: {image_path}")
        except Exception as e:
            logger.error(f"处理图片失败 {image_path}: {e}")
            raise
    
    messages.append({
        "role": "user",
        "content": user_content
    })
    
    # 构建请求体
    request_body = {
        "model": settings.model_name,
        "temperature": 0.2,
        "messages": messages
    }
    
    # 为OpenRouter添加max_tokens限制
    if settings.use_openrouter:
        request_body["max_tokens"] = 500  # 限制输出长度以控制费用
    
    # 构建请求头
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json"
    }
    
    # 根据服务类型添加特定头部
    if settings.use_openrouter:
        headers["HTTP-Referer"] = "https://github.com/your-repo/minimax-tagger"
        headers["X-Title"] = "MiniMax Tagger"
    elif settings.group_id:
        headers["X-Group-ID"] = settings.group_id
    
    # 发送 HTTP 请求（使用重试机制）
    async def make_request():
        # 创建SSL上下文，跳过证书验证（解决macOS SSL问题）
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        timeout = aiohttp.ClientTimeout(total=60)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            logger.debug(f"发送 MiniMax API 请求，图片数量: {len(image_paths)}")
            
            async with session.post(
                settings.api_base_url,
                json=request_body,
                headers=headers
            ) as response:
                # 记录响应状态
                logger.debug(f"MiniMax API 响应状态: {response.status}")
                
                if response.status == 429:
                    # 速率限制，抛出特定异常以便重试
                    raise aiohttp.ClientError(f"API 速率限制: {response.status}")
                
                response.raise_for_status()
                result = await response.json()
                
                logger.info(f"MiniMax API 调用成功，图片数量: {len(image_paths)}")
                return result
    
    # 使用重试机制调用 API
    return await retry_async(
        make_request,
        max_retries=settings.retry_max,
        base_delay=settings.retry_delay
    )


async def extract_prompt_from_response(api_response: Dict[str, Any]) -> str:
    """从 API 响应中提取生成的提示词。"""
    try:
        # 首先检查是否是错误响应
        if "error" in api_response:
            error_info = api_response["error"]
            if isinstance(error_info, dict):
                error_message = error_info.get("message", "未知错误")
                error_code = error_info.get("code", "未知代码")
                raise ValueError(f"API调用失败: {error_message} (代码: {error_code})")
            else:
                raise ValueError(f"API调用失败: {error_info}")
        
        # 根据 MiniMax API 响应格式提取内容
        if "choices" in api_response and len(api_response["choices"]) > 0:
            choice = api_response["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                return choice["message"]["content"].strip()
        
        # 备用提取方式
        if "reply" in api_response:
            return api_response["reply"].strip()
        
        # 如果都没找到，返回错误信息
        raise ValueError(f"无法从API响应中提取内容，响应格式: {list(api_response.keys())}")
        
    except ValueError:
        # 重新抛出 ValueError
        raise
    except Exception as e:
        raise ValueError(f"解析API响应时出错: {str(e)}") 