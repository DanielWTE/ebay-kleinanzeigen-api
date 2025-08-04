import os
from fastapi import FastAPI, Depends
from routers import inserate, inserat
from utils.auth import verify_token

app = FastAPI(
    version="1.1.0",
    title="Kleinanzeigen API",
    description="A secure API for scraping Kleinanzeigen data. All endpoints require x-token header authentication.",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Kleinanzeigen API",
        "endpoints": [
            "/inserate",
            "/inserat/{id}"
        ],
        "authentication": "All endpoints require 'x-token' header for authentication"
    }

# Include routers with authentication dependency
app.include_router(inserate.router, dependencies=[Depends(verify_token)])
app.include_router(inserat.router, dependencies=[Depends(verify_token)])
