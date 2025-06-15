from pydantic import BaseModel
from typing import List, Optional

class CompanyNameResponse(BaseModel):
    name: str

class CompanyResponse(BaseModel):
    company_id: str
    address: str
    company_name: str
    email: str
    phone: str
    created_at: str

class ServiceResponse(BaseModel):
    service_name: str
    price: float

class BranchResponse(BaseModel):
    branch_name: str
    address: str
    phone: str
    manager: str
    services: List[ServiceResponse]

class BranchWithoutServicesResponse(BaseModel):
    branch_name: str
    address: str
    phone: str
    manager: str
class ProviderResponse(BaseModel):
    company: CompanyNameResponse
    branches: List[BranchWithoutServicesResponse]

class ProviderDetailResponse(BaseModel):
    company: CompanyResponse
    branches: List[BranchResponse]