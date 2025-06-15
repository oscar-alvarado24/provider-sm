from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from app.models.provider import Provider, Company, Branch, Service
from app.models.request_models import ProviderRequest, CompanyRequest, BranchRequest, ServiceRequest
from app.models.response_models import ProviderResponse, ProviderDetailResponse
from app.services.dynamodb_service import DynamoDBService
from app.config import settings as app_settings

def get_db_service():
    """Dependency to get DynamoDB service"""
    try:
        service = DynamoDBService(
            region_name=app_settings.aws_region_name,
            endpoint_url=app_settings.dynamodb_endpoint_url
        )
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

def convert_request_to_provider(provider_request: ProviderRequest) -> Provider:
    """Convierte SupplierRequest a Provider usando el company_id del objeto company"""
    
    # Create Company with company_id from request
    company = create_company(provider_request.company)
    # Create Branches with services
    branches = []

    for branch_request in provider_request.branches:
        branch = create_branch(branch_request)
        branches.append(branch)    
    
    return Provider(
        company=company,
        branches=branches
    )

def create_company(company_request: CompanyRequest) -> Company:
    """Create Company from CompanyRequest"""
    return Company(
        company_id=company_request.company_id,
        company_name=company_request.company_name,
        email=company_request.email,
        phone=company_request.phone,
        address=company_request.address
    )
def create_branch(branch_request: BranchRequest) -> Branch:
    """Create Branch from BranchRequest"""
    branch_services = []
    for service_request in branch_request.services:
        branch_services.append(create_service(service_request))
    return Branch(
        branch_name=branch_request.branch_name,
        city=branch_request.city,
        address=branch_request.address,
        phone=branch_request.phone,
        manager=branch_request.manager,
        services=branch_services
    )
def create_service(service_request: ServiceRequest) -> Service:
        """Create Service from ServiceRequest"""
        return Service(
            service_name=service_request.service_name,
            price=service_request.price
        )
router = APIRouter(
    prefix="/providers",
    tags=["Providers"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=str, status_code=status.HTTP_201_CREATED, 
             summary="Create new provider")
async def create_provider_endpoint(
    provider_request: ProviderRequest, 
    db_service: DynamoDBService = Depends(get_db_service)
):
    """
    Create a new provider with the given details.
    """
    try:
    # Convertir request a modelo interno
        provider = convert_request_to_provider(provider_request)
        
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

@router.get("/{company_id}", response_model=ProviderDetailResponse, 
            summary="Get provider by ID")
async def get_provider_endpoint(
    company_id: str,
    db_service: DynamoDBService = Depends(get_db_service)
):
    """Get provider by company ID"""
    try:
        return db_service.get_provider_by_id(company_id)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error get provider {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )


@router.put("/{company_id}", response_model=str, 
            summary="Update provider")
async def update_provider_endpoint(
    company_id: str,
    company_request: CompanyRequest,
    db_service: DynamoDBService = Depends(get_db_service)
):
    """Actualiza un proveedor completo"""
    try:
        company= create_company(company_request)
        print(f"Updating provider with ID {company_id} with data: {company}")
        updated_provider = db_service.update_company_provider(company_id, company)
        return updated_provider
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error get provider {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT,
               summary="Delete provider")
async def delete_provider_endpoint(
    company_id: str,
    db_service: DynamoDBService = Depends(get_db_service)
):
    """Elimina un proveedor y todos sus datos relacionados"""
    try:
        success = db_service.delete_provider(company_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Proveedor con ID {company_id} no encontrado"
            )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error deleting provider {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )

@router.get("/search/service-city", response_model=List[ProviderResponse ],
            summary="Search providers by service and city")
async def search_providers_endpoint(
    service_name: str,
    city: str,
    db_service: DynamoDBService = Depends(get_db_service)
):
    """Busca proveedores que ofrecen un servicio específico en una ciudad"""
    try:
        providers = db_service.search_providers_by_service_and_city(service_name, city)
        return providers
    except Exception as e:
        print(f"Error searching providers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}"
        )