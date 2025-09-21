import asyncio
import time
from functools import wraps
from typing import Callable, Any

def timer(func: Callable) -> Callable:
    """Decorator to time function execution"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        start_time = time.time()
        result = await func(*args, **kwargs)
        end_time = time.time()
        print(f"{func.__name__} executed in {end_time - start_time:.4f} seconds")
        return result
    return wrapper

def memory_profiler(func: Callable) -> Callable:
    """Decorator to profile memory usage"""
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        # In a real implementation, this would use memory-profiler
        result = await func(*args, **kwargs)
        return result
    return wrapper

class PerformanceMonitor:
    def __init__(self):
        pass
    
    async def measure_async_operation(self, operation, *args, **kwargs):
        """Measure execution time of async operations"""
        start_time = time.time()
        result = await operation(*args, **kwargs)
        end_time = time.time()
        return {
            "result": result,
            "execution_time": end_time - start_time
        }
