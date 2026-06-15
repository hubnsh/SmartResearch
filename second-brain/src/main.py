from fastapi import FastAPI
from src.core.config import settings
from src.api.routes import router

app = FastAPI(
    title=settings.APP_NAME,
    description="An intelligent Second Brain Agent with KG and RAG",
    version="0.1.0"
)

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {
        "message": "Welcome to Second Brain Agent API",
        "status": "running",
        "env": settings.APP_ENV
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8001, reload=True)
