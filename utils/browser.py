import asyncio
from typing import List
from playwright.async_api import async_playwright, BrowserContext, Page
from utils.user_agent import get_random_ua


class PlaywrightManager:
    def __init__(self):
        self._playwright = None
        self._browser = None

    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

    async def new_context_page(self):
        context = await self._browser.new_context(user_agent=get_random_ua())
        return await context.new_page()

    async def close_page(self, page):
        await page.close()

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()


class OptimizedPlaywrightManager:
    def __init__(self, max_contexts: int = 10, max_concurrent: int = 5):
        self._playwright = None
        self._browser = None
        self._context_pool: List[BrowserContext] = []
        self._context_in_use: List[BrowserContext] = []
        self._max_contexts = max_contexts
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._context_lock = asyncio.Lock()

        # Performance metrics
        self._contexts_created = 0
        self._contexts_reused = 0
        self._concurrent_operations = 0
        self._max_concurrent_reached = 0

    async def start(self):
        """Initialize the browser and create initial context pool"""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

        # Pre-create some contexts for the pool
        initial_contexts = min(3, self._max_contexts)
        for _ in range(initial_contexts):
            context = await self._browser.new_context(user_agent=get_random_ua())
            self._context_pool.append(context)
            self._contexts_created += 1

    async def get_context(self) -> BrowserContext:
        """Get a browser context from the pool or create a new one"""
        async with self._context_lock:
            if self._context_pool:
                context = self._context_pool.pop()
                self._context_in_use.append(context)
                self._contexts_reused += 1
                return context

            # Create new context if pool is empty and under limit
            if len(self._context_in_use) < self._max_contexts:
                context = await self._browser.new_context(user_agent=get_random_ua())
                self._context_in_use.append(context)
                self._contexts_created += 1
                return context

            # If we're at the limit, wait and try again
            await asyncio.sleep(0.1)
            return await self.get_context()

    async def release_context(self, context: BrowserContext):
        """Return a context to the pool for reuse"""
        async with self._context_lock:
            if context in self._context_in_use:
                self._context_in_use.remove(context)

                # Close all pages in the context to clean it up
                for page in context.pages:
                    await page.close()

                # Add back to pool if under limit, otherwise close it
                if len(self._context_pool) < self._max_contexts // 2:
                    self._context_pool.append(context)
                else:
                    await context.close()

    async def execute_with_semaphore(self, coro):
        """Execute a coroutine with concurrency control"""
        async with self._semaphore:
            self._concurrent_operations += 1
            self._max_concurrent_reached = max(
                self._max_concurrent_reached, self._concurrent_operations
            )
            try:
                result = await coro
                return result
            finally:
                self._concurrent_operations -= 1

    async def new_context_page(self) -> Page:
        """Create a new page using context pooling (backward compatibility)"""
        context = await self.get_context()
        page = await context.new_page()
        # Store context reference on page for cleanup
        page._context_ref = context
        return page

    async def close_page(self, page: Page):
        """Close a page and return its context to the pool"""
        context = getattr(page, "_context_ref", None)
        await page.close()
        if context:
            await self.release_context(context)

    def get_performance_metrics(self) -> dict:
        """Get current performance metrics"""
        return {
            "contexts_created": self._contexts_created,
            "contexts_reused": self._contexts_reused,
            "contexts_in_pool": len(self._context_pool),
            "contexts_in_use": len(self._context_in_use),
            "max_contexts": self._max_contexts,
            "max_concurrent_reached": self._max_concurrent_reached,
            "current_concurrent": self._concurrent_operations,
            "reuse_ratio": self._contexts_reused / max(self._contexts_created, 1),
        }

    async def close(self):
        """Clean up all resources"""
        # Close all contexts in pool
        for context in self._context_pool:
            await context.close()

        # Close all contexts in use
        for context in self._context_in_use:
            await context.close()

        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._context_pool.clear()
        self._context_in_use.clear()
