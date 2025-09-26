from fastapi import FastAPI
from app.routers import provider_router
from app.core.config import settings
import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A microservice for managing provider information using FastAPI and DynamoDB."
)

# Include the providers router
app.include_router(provider_router.router)

@app.get("/", tags=["Root"])
async def root():
    return {"message": f"Welcome to the {settings.app_name} v{settings.app_version}"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8050,
        reload=True
    )