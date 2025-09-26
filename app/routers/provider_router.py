from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from app.entities.provider import Provider, Company, Branch, Service
from app.services.dynamodb_service import DynamoDBService
from app.core.config import settings as app_settings

def get_db_service():
    """Dependency to get DynamoDB service"""
    try:
        service = DynamoDBService()
        return service
    except ConnectionError as e:
        print(f"CRITICAL: Failed to initialize DynamoDBService: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Could not connect to the database service: {e}"
        )
    except Exception as e:
        print(f"CRITICAL: Unexpected error during DynamoDBService instantiation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while setting up the database service: {e}"
        )

router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)

@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED, 
             summary="Create new provider")
async def create_provider_endpoint(
    provider: Provider, 
    db_service: DynamoDBService = Depends(get_db_service)
):
    """
    Create a new provider with the given details.
    """
    try:        
        # Crear el proveedor
        created_provider = db_service.create_provider(provider)
        return created_provider
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating provider {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/{company_id}", response_model=Provider, 
            summary="Get provider by ID")
async def get_provider_endpoint(
    company_id: str,
    db_service: DynamoDBService = Depends(get_db_service)
):
    """Get provider by company ID"""
    try:
        print(f"Fetching provider with ID: {company_id}")
        return db_service.get_provider_by_id(company_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error get provider {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )
@router.put("/update-company/{company_id}", response_model=str,
            summary="Update company information")
async def update_company_endpoint(
    company_id: str,
    company: Company,
    db_service: DynamoDBService = Depends(get_db_service)
):
    """Update company information"""
    try:
        return db_service.update_company(company_id, company)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error updating company {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

