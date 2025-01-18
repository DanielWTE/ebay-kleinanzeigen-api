from fastapi import FastAPI
from routers import inserate, inserat

app = FastAPI(
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to the Kleinanzeigen API",
        "endpoints": [
            "/inserate",
            "/inserat/{id}"
        ]
    }

app.include_router(inserate.router)
app.include_router(inserat.router) 