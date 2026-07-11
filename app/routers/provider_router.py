import logging
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, List
from app.entities.provider import Provider, Company, Branch
from app.helper.branch_data import BranchData
from app.helper.crypto import CryptoService
from app.middlewares.auth.dependencies import require_groups
from app.services.dynamodb_service import DynamoDBService
from app.core.config import settings

logger = logging.getLogger(__name__)

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

def get_cripto_instance():
    try:
        crypto_instance = CryptoService(settings.secret_key)
        return crypto_instance
    except Exception as e:
        print(f"error: {e}")
router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
)

@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED,
             summary="Create new provider")
async def create_provider_endpoint(
    provider: Provider,
    db_service: DynamoDBService = Depends(get_db_service),
    current_user: Dict = Depends(require_groups(["pacientes"]))
):
    """
    Create a new provider with the given details.
    """
    try:
        print(f"Creating provider: {provider.company.company_name}")
        # Crear el proveedor
        validations_branch_unique = db_service._validate_branches_unique( [branch.branch_id for branch in provider.branches])
        if len(validations_branch_unique)>0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail= list(validations_branch_unique)
            )
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

@router.get("/company/{company_id}", response_model=Provider,
            summary="Get provider by ID")
async def get_provider_endpoint(
    company_id: str,
    db_service: DynamoDBService = Depends(get_db_service),
    current_user: Dict = Depends(require_groups(["pacientes"]))
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

@router.get("/branches", response_model=List[Branch],
            summary="Get a branches by company id and branch id")
async def get_branch_endpoint(
    keys: str = Query(..., description="Listado de claves company_id | branch_id"),
    db_service: DynamoDBService = Depends(get_db_service),
    current_user: Dict = Depends(require_groups(["pacientes"])),
    cripto_service: CryptoService = Depends(get_cripto_instance)
):
    """Get branch by company ID and branch ID"""
    try:
        logger.debug('El valor recivido es: {keys}')
        keys_decripted= cripto_service.decrypt(keys)
        keys_list = keys_decripted.split(",")
        logger.debug("Keys after decryption: {keys_list}")
        branches_data=[]
        for branch_str in keys_list:
            if " | " in branch_str:
                company_id, branch_id = branch_str.split(" | ", 1)
                logger.debug(f"se recibe el compani id {company_id} y el branch id {branch_id}")
                branches_data.append(BranchData(
                    company_id=company_id.strip(),
                    branch_id=branch_id.strip()
                ))
        return db_service.get_branches([branch.model_dump() for branch in branches_data])
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error get branches: {e}")
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

