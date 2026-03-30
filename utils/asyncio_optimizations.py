"""
Advanced asyncio optimizations based on high-performance patterns.

This module implements the advanced asyncio techniques from production systems
to maximize performance and minimize memory usage.
"""

import asyncio
import time
import gc
import weakref
from typing import List, Callable, Any, Optional, Dict
from contextlib import asynccontextmanager
from dataclasses import dataclass
from functools import partial


@dataclass
class TaskMetrics:
    """Metrics for individual task performance."""

    task_id: str
    start_time: float
    end_time: float
    success: bool
    memory_usage: Optional[int] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class HighPerformanceTaskManager:
    """
    Advanced task manager implementing production-grade asyncio patterns.

    Features:
    - Automatic task cleanup to prevent memory leaks
    - Graceful cancellation with timeout
    - Memory-conscious processing with semaphores
    - Task reference management using weak references
    """

    def __init__(self, max_concurrent: int = 10):
        self.tasks: weakref.WeakSet = weakref.WeakSet()
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self._task_metrics: Dict[str, TaskMetrics] = {}
        self._cleanup_interval = 30.0  # seconds
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_task(self, coro, task_id: str = None) -> asyncio.Task:
        """Create a task with automatic cleanup and metrics tracking."""
        if task_id is None:
            task_id = f"task_{id(coro)}"

        task = asyncio.create_task(coro)
        self.tasks.add(task)

        # Track task metrics
        self._task_metrics[task_id] = TaskMetrics(
            task_id=task_id, start_time=time.time(), end_time=0, success=False
        )

        # Add completion callback for cleanup and metrics
        task.add_done_callback(partial(self._task_completed_callback, task_id))

        return task

    def _task_completed_callback(self, task_id: str, task: asyncio.Task):
        """Callback for when a task completes."""
        if task_id in self._task_metrics:
            metrics = self._task_metrics[task_id]
            metrics.end_time = time.time()
            metrics.success = not task.cancelled() and task.exception() is None

            # Log any unhandled exceptions
            if not metrics.success and not task.cancelled():
                try:
                    task.result()  # This will raise the exception
                except Exception as e:
                    # In production, you'd log this properly
                    print(f"Task {task_id} failed: {e}")

    async def execute_with_semaphore(self, coro, task_id: str = None):
        """Execute a coroutine with semaphore control."""
        async with self.semaphore:
            if task_id:
                task = self.create_task(coro, task_id)
                return await task
            else:
                return await coro

    async def gather_with_limit(self, coroutines: List, return_exceptions: bool = True):
        """
        Execute multiple coroutines with concurrency limiting.

        This prevents memory explosion from too many concurrent operations.
        """
        tasks = []
        for i, coro in enumerate(coroutines):
            task_id = f"batch_task_{i}"
            task = self.create_task(self.execute_with_semaphore(coro, task_id), task_id)
            tasks.append(task)

        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)

    async def cancel_all(self, timeout: float = 5.0):
        """Gracefully cancel all tasks with timeout."""
        if not self.tasks:
            return

        # Cancel all tasks
        for task in list(self.tasks):
            if not task.done():
                task.cancel()

        # Wait for graceful cancellation with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*list(self.tasks), return_exceptions=True),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            # Force kill any remaining tasks
            for task in list(self.tasks):
                if not task.done():
                    task.cancel()

            # Final cleanup
            await asyncio.gather(*list(self.tasks), return_exceptions=True)

    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for all tasks."""
        completed_tasks = [m for m in self._task_metrics.values() if m.end_time > 0]

        if not completed_tasks:
            return {"total_tasks": 0}

        durations = [t.duration for t in completed_tasks]
        success_count = sum(1 for t in completed_tasks if t.success)

        return {
            "total_tasks": len(completed_tasks),
            "successful_tasks": success_count,
            "failed_tasks": len(completed_tasks) - success_count,
            "success_rate": (success_count / len(completed_tasks)) * 100,
            "average_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "active_tasks": len(
                [t for t in self._task_metrics.values() if t.end_time == 0]
            ),
        }


class EventLoopOptimizer:
    """
    Event loop optimization utilities for maximum performance.
    """

    @staticmethod
    def setup_uvloop():
        """Setup uvloop for 2-4x performance improvement."""
        try:
            import uvloop

            asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
            return True
        except ImportError:
            print("uvloop not available, using default event loop")
            return False

    @staticmethod
    def optimize_event_loop():
        """Apply event loop optimizations."""
        loop = asyncio.get_event_loop()

        # Set slow callback duration for debugging
        loop.slow_callback_duration = 0.1

        # Enable debug mode in development
        if __debug__:
            loop.set_debug(True)

        return loop


class MemoryOptimizedProcessor:
    """
    Memory-conscious processor that prevents memory leaks and optimizes GC.

    Implements the patterns from the Medium article for production-grade
    memory management in asyncio applications.
    """

    def __init__(self, max_concurrent: int = 50, gc_threshold: int = 1000):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.processed_count = 0
        self.gc_threshold = gc_threshold
        self.task_manager = HighPerformanceTaskManager(max_concurrent)

    async def process_batch(
        self, items: List[Any], processor_func: Callable
    ) -> List[Any]:
        """
        Process a batch of items with memory optimization.

        Args:
            items: List of items to process
            processor_func: Async function to process each item

        Returns:
            List of processed results
        """

        async def process_item_with_cleanup(item, index):
            """Process single item with automatic cleanup."""
            try:
                async with self.semaphore:
                    result = await processor_func(item)

                    # Periodic garbage collection to prevent memory buildup
                    self.processed_count += 1
                    if self.processed_count % self.gc_threshold == 0:
                        gc.collect()

                    return result
            except Exception as e:
                # Return exception for gather to handle
                return e

        # Create tasks with the task manager for proper cleanup
        coroutines = [
            process_item_with_cleanup(item, i) for i, item in enumerate(items)
        ]

        # Execute with controlled concurrency
        results = await self.task_manager.gather_with_limit(coroutines)

        # Separate successful results from exceptions
        successful_results = []
        exceptions = []

        for result in results:
            if isinstance(result, Exception):
                exceptions.append(result)
            else:
                successful_results.append(result)

        # Force garbage collection after batch processing
        gc.collect()

        return successful_results, exceptions

    async def cleanup(self):
        """Clean up resources."""
        await self.task_manager.cancel_all()
        gc.collect()


@asynccontextmanager
async def optimized_asyncio_context(max_concurrent: int = 10):
    """
    Context manager for optimized asyncio operations.

    Usage:
        async with optimized_asyncio_context(max_concurrent=20) as optimizer:
            results = await optimizer.process_batch(items, process_func)
    """
    # Setup uvloop for performance
    EventLoopOptimizer.setup_uvloop()

    # Create optimized processor
    processor = MemoryOptimizedProcessor(max_concurrent)

    try:
        yield processor
    finally:
        await processor.cleanup()


class ConnectionPoolManager:
    """
    High-performance connection pool manager for HTTP operations.

    Implements the connection reuse patterns from the Medium article.
    """

    def __init__(self, max_connections: int = 100, max_per_host: int = 30):
        self.max_connections = max_connections
        self.max_per_host = max_per_host
        self._session = None

    async def get_session(self):
        """Get or create optimized HTTP session."""
        if self._session is None:
            import aiohttp

            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_per_host,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )

            timeout = aiohttp.ClientTimeout(total=30, connect=5, sock_read=10)

            self._session = aiohttp.ClientSession(connector=connector, timeout=timeout)

        return self._session

    async def close(self):
        """Close the session and cleanup connections."""
        if self._session:
            await self._session.close()
            self._session = None


# Decorator for monitoring slow coroutines
def monitor_slow_coroutines(threshold: float = 0.1):
    """
    Decorator to monitor and log slow coroutines.

    Args:
        threshold: Time threshold in seconds to consider a coroutine slow
    """

    def decorator(func):
        import functools

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                if duration > threshold:
                    print(f"Slow coroutine: {func.__name__} took {duration:.3f}s")

        return wrapper

    return decorator


# Example usage functions
async def example_optimized_processing():
    """Example of how to use the optimized asyncio patterns."""

    async def sample_work_item(item):
        """Simulate some async work."""
        await asyncio.sleep(0.1)  # Simulate I/O
        return f"processed_{item}"

    # Use the optimized context
    async with optimized_asyncio_context(max_concurrent=20) as optimizer:
        items = list(range(100))

        successful_results, exceptions = await optimizer.process_batch(
            items, sample_work_item
        )

        print(f"Processed {len(successful_results)} items successfully")
        print(f"Had {len(exceptions)} exceptions")

        # Get performance metrics
        metrics = optimizer.task_manager.get_metrics()
        print(f"Task metrics: {metrics}")


if __name__ == "__main__":
    # Example of running with uvloop optimization
    EventLoopOptimizer.setup_uvloop()
    asyncio.run(example_optimized_processing())
