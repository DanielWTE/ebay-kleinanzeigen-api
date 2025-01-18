from playwright.async_api import async_playwright
from utils.user_agent import get_random_ua

class PlaywrightManager:
    def __init__(self):
        self._playwright = None
        self._browser = None
        
    async def start(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        
    async def new_context_page(self):
        context = await self._browser.new_context(
            user_agent=get_random_ua()
        )
        return await context.new_page()
        
    async def close_page(self, page):
        await page.close()
        
    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
            