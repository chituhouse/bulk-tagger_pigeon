"""并发控制工具 - 重试、限流等。"""
from __future__ import annotations

import asyncio
import random
from typing import Any, Callable, Optional
from functools import wraps

from .logger import get_logger

logger = get_logger(__name__)


class RetryError(Exception):
    """重试失败异常"""
    pass


async def retry_async(
    func: Callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    **kwargs
) -> Any:
    """异步重试函数
    
    Args:
        func: 要重试的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟时间（秒）
        max_delay: 最大延迟时间（秒）
        
    Returns:
        函数执行结果
        
    Raises:
        RetryError: 重试次数用完仍然失败
    """
    last_exception = None
    
    for attempt in range(max_retries + 1):
        try:
            return await func(*args, **kwargs)
                
        except Exception as e:
            last_exception = e
            
            if attempt == max_retries:
                logger.error(f"重试失败，已达到最大重试次数 {max_retries}: {e}")
                raise RetryError(f"重试 {max_retries} 次后仍然失败: {e}") from e
            
            # 计算延迟时间（指数退避）
            delay = min(base_delay * (2 ** attempt), max_delay)
            
            # 添加随机抖动
            delay *= (0.5 + random.random() * 0.5)
            
            logger.warning(f"第 {attempt + 1} 次尝试失败，{delay:.2f}秒后重试: {e}")
            await asyncio.sleep(delay)
    
    # 这个分支理论上不会到达
    raise RetryError(f"未知错误: {last_exception}")


class AsyncRateLimiter:
    """异步限流器"""
    
    def __init__(self, calls: int, period: float):
        """
        Args:
            calls: 允许的调用次数
            period: 时间窗口（秒）
        """
        self.calls = calls
        self.period = period
        self.call_times: list[float] = []
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """获取调用许可"""
        async with self._lock:
            now = asyncio.get_event_loop().time()
            
            # 清理过期的调用记录
            self.call_times = [t for t in self.call_times if now - t < self.period]
            
            # 如果达到限制，等待
            if len(self.call_times) >= self.calls:
                sleep_time = self.period - (now - self.call_times[0])
                if sleep_time > 0:
                    logger.debug(f"触发限流，等待 {sleep_time:.2f} 秒")
                    await asyncio.sleep(sleep_time)
                    return await self.acquire()
            
            # 记录此次调用
            self.call_times.append(now)


class ConcurrencyLimiter:
    """并发限制器"""
    
    def __init__(self, max_concurrency: int):
        self.semaphore = asyncio.Semaphore(max_concurrency)
        self.max_concurrency = max_concurrency
        self.active_tasks = 0
    
    async def __aenter__(self):
        await self.semaphore.acquire()
        self.active_tasks += 1
        logger.debug(f"获取并发许可，当前活跃任务: {self.active_tasks}/{self.max_concurrency}")
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.active_tasks -= 1
        self.semaphore.release()
        logger.debug(f"释放并发许可，当前活跃任务: {self.active_tasks}/{self.max_concurrency}")


async def run_tasks_with_limit(
    tasks: list[Callable],
    max_concurrency: int,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> list[tuple[Any, Optional[Exception]]]:
    """并发运行任务，限制最大并发数
    
    Args:
        tasks: 任务列表
        max_concurrency: 最大并发数
        progress_callback: 进度回调函数
        
    Returns:
        任务结果列表，每个元素为 (result, error)
    """
    limiter = ConcurrencyLimiter(max_concurrency)
    results: list[tuple[Any, Optional[Exception]]] = []
    completed = 0
    
    async def run_single_task(task, index):
        nonlocal completed
        async with limiter:
            try:
                if asyncio.iscoroutinefunction(task):
                    result = await task()
                else:
                    result = task()
                
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(tasks))
                
                return index, result, None
                
            except Exception as e:
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(tasks))
                
                logger.error(f"任务 {index} 执行失败: {e}")
                return index, None, e
    
    # 创建所有任务协程
    coroutines = [run_single_task(task, i) for i, task in enumerate(tasks)]
    
    # 执行所有任务
    try:
        task_results = await asyncio.gather(*coroutines, return_exceptions=True)
        
        # 整理结果，按索引排序
        indexed_results = [(None, Exception("任务未执行"))] * len(tasks)
        for task_result in task_results:
            if isinstance(task_result, Exception):
                logger.error(f"任务执行异常: {task_result}")
                continue
            
            if isinstance(task_result, tuple) and len(task_result) == 3:
                index, result, error = task_result
                indexed_results[index] = (result, error)
        
        return indexed_results
        
    except Exception as e:
        logger.error(f"批量任务执行失败: {e}")
        # 返回错误结果
        return [(None, e) for _ in tasks] 