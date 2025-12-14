"""
Module that contain start configurations for deploy microservice
"""
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routers import provider_router
from app.core.config import settings

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A microservice for managing provider information using FastAPI and DynamoDB."
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.get_origin_regex(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Custom-Header"],
    max_age=3600,
)
@app.options("/{full_path:path}")
async def options_handler():
    """
    Function for define json response
    """
    return JSONResponse(
        content={},
        status_code=200
    )
# Include the providers router
app.include_router(provider_router.router)

@app.get("/health", tags=["Root"])
async def root():
    """
    path for create a heath endpoint
    """
    return {"message": f"Welcome to the {settings.app_name} v{settings.app_version}"}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8050,
        reload=False
    )
