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

# Optional: Add a startup event to create DynamoDB table if running locally
# This is just an example; for production, table creation should be managed by IaC tools.
# @app.on_event("startup")
# async def startup_event():
#     if settings.dynamodb_endpoint_url: # Indicates local development
#         print(f"Running in local mode with endpoint: {settings.dynamodb_endpoint_url}")
#         print(f"Attempting to ensure table '{settings.dynamodb_table_name}' exists...")
#         try:
#             # Note: DynamoDBService expects env vars to be set for its own init.
#             # For this startup event, ensure they are available or pass them directly.
#             # This is a simplified example.
#             os.environ.setdefault("DYNAMODB_TABLE_NAME", settings.dynamodb_table_name)
#             if settings.aws_region_name:
#                  os.environ.setdefault("AWS_REGION_NAME", settings.aws_region_name)
#             if settings.dynamodb_endpoint_url:
#                  os.environ.setdefault("DYNAMODB_ENDPOINT_URL", settings.dynamodb_endpoint_url)

#             service = DynamoDBService(
#                 table_name=settings.dynamodb_table_name,
#                 region_name=settings.aws_region_name,
#                 endpoint_url=settings.dynamodb_endpoint_url
#             )
#             service._create_table_if_not_exists() # Assuming you add this helper in DynamoDBService
#             print(f"Table '{settings.dynamodb_table_name}' checked/created.")
#         except Exception as e:
#             print(f"Error during table creation check: {e}")
#     else:
#         print("Running in deployed mode (DynamoDB table expected to exist).")
