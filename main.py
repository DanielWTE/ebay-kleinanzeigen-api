import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from routers import (
    convert_url,
    inserat,
    inserate_batch,
    inserate_by_url,
    inserate_detailed_ultra,
    inserate_ultra,
)
from schemas import RootResponse
from utils.asyncio_optimizations import EventLoopOptimizer
from utils.browser import OptimizedPlaywrightManager

# Single source of truth for the public API routers: used both to register
# routes and to advertise them in the root response.
_ROUTER_MODULES = (
    inserate_ultra,
    inserat,
    inserate_detailed_ultra,
    inserate_batch,
    convert_url,
    inserate_by_url,
)

# Global browser manager instance for sharing across all endpoints
browser_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - startup and shutdown events"""
    global browser_manager

    # Setup uvloop for maximum performance (2-4x improvement)
    uvloop_enabled = EventLoopOptimizer.setup_uvloop()

    # Optimize event loop settings
    EventLoopOptimizer.optimize_event_loop()

    # Startup: Initialize shared browser manager with optimized settings
    browser_manager = OptimizedPlaywrightManager(max_contexts=20, max_concurrent=10)
    try:
        await browser_manager.start()
    except NotImplementedError as exc:
        # Windows + `uvicorn --reload`/`--workers` runs a SelectorEventLoop,
        # which cannot spawn the Playwright driver subprocess (issue #15).
        if sys.platform == "win32":
            raise RuntimeError(
                "Playwright cannot start on this event loop. On Windows, run "
                "`uvicorn main:app` without --reload/--workers, or use Docker."
            ) from exc
        raise

    # Store browser manager in app state for access by routers
    app.state.browser_manager = browser_manager
    app.state.uvloop_enabled = uvloop_enabled

    yield

    # Shutdown: Clean up browser resources
    if browser_manager:
        await browser_manager.close()


app = FastAPI(version="1.0.0", lifespan=lifespan)


@app.get("/", response_model=RootResponse)
async def root():
    return {
        "message": "Welcome to the Kleinanzeigen API",
        "endpoints": [
            route.path for module in _ROUTER_MODULES for route in module.router.routes
        ],
        "status": "operational",
    }


for _module in _ROUTER_MODULES:
    app.include_router(_module.router)
