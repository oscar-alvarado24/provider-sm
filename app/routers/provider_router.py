from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    ProviderNameResponse,
    ProviderFilterQueryParams
)
from app.services.dynamodb_service import DynamoDBService
import os # For environment variables if needed directly here, though service handles it

# Dependency to get DynamoDB service
# This helps in managing the lifecycle of the service if needed,
# and makes it easier to mock for testing.
def get_db_service():
    # These environment variables should be set for the DynamoDBService to work
    # Ensure DYNAMODB_TABLE_NAME, AWS_REGION_NAME are set.
    # DYNAMODB_ENDPOINT_URL is optional (for local DynamoDB)
    # The DynamoDBService class already has defaults and handles os.getenv
    return DynamoDBService()

router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=ProviderResponse, status_code=status.HTTP_201_CREATED, summary="Create new provider")
async def create_provider_endpoint(provider: ProviderCreate, db_service: DynamoDBService = Depends(get_db_service)):
    try:
        created_provider = db_service.create_provider(provider)
        return created_provider
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{provider_id}", response_model=ProviderResponse, summary="Get provider by ID")
async def get_provider_endpoint(provider_id: str, db_service: DynamoDBService = Depends(get_db_service)):
    try:
        provider = db_service.get_provider_by_id(provider_id)
        if not provider:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        return provider
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

@router.put("/{provider_id}", response_model=ProviderResponse, summary="Update existing provider")
async def update_provider_endpoint(provider_id: str, provider_update: ProviderUpdate, db_service: DynamoDBService = Depends(get_db_service)):
    try:
        updated_provider = db_service.update_provider(provider_id, provider_update)
        if not updated_provider:
            # This also handles the case where the provider_id doesn't exist and update_provider returns None
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found or update failed")
        return updated_provider
    except ValueError as ve: # Catch validation errors from Pydantic models if any slip through or are raised in service
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(ve))
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete provider by ID")
async def delete_provider_endpoint(provider_id: str, db_service: DynamoDBService = Depends(get_db_service)):
    try:
        success = db_service.delete_provider(provider_id)
        if not success:
            # This means the provider was not found to be deleted.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        # For 204 No Content, FastAPI expects no return value (or None)
        return None
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/", response_model=List[ProviderResponse], summary="Filter providers by city and service")
async def filter_providers_endpoint(params: ProviderFilterQueryParams = Depends(), db_service: DynamoDBService = Depends(get_db_service)):
    # The ProviderFilterQueryParams model will ensure 'city' and 'service' are provided due to Field(...)
    try:
        providers = db_service.get_providers_by_city_and_service(city=params.city, service=params.service)
        return providers
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/{provider_id}/name", response_model=ProviderNameResponse, summary="Get provider name by ID")
async def get_provider_name_endpoint(provider_id: str, db_service: DynamoDBService = Depends(get_db_service)):
    try:
        provider_name_info = db_service.get_provider_name_by_id(provider_id)
        if not provider_name_info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")
        return provider_name_info
    except Exception as e:
        # Log the exception e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
