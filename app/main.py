from fastapi import FastAPI
from app.routers import provider_router
from app.config import settings
# If you plan to use DynamoDB local for development and want to create the table on startup:
# from app.services.dynamodb_service import DynamoDBService 
# import os

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
