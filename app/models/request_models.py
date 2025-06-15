from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal

class CompanyRequest(BaseModel):
    """Modelo para la creación de empresa"""
    company_id: str
    address: str
    company_name: str
    email: str
    phone: str

class ServiceRequest(BaseModel):
    """Modelo para la creación de servicio (sin company_id que se asigna automáticamente)"""
    service_name: str
    price: Decimal

class BranchRequest(BaseModel):
    """Modelo para la creación de sucursal (sin company_id que se asigna automáticamente)"""
    city: str
    branch_name: str
    address: str
    phone: str
    services: List[ServiceRequest]
    manager: Optional[str] = None

class ProviderRequest(BaseModel):
    """Modelo para la creación de proveedor completo"""
    company: CompanyRequest
    branches: List[BranchRequest]

    class Config:
        json_schema_extra = {
            "example": {
                "company": {
                    "company_id": "tech-solutions-001",
                    "address": "Calle 100 #15-30, Zona Rosa - Bogotá, Colombia",
                    "company_name": "TechSolutions S.A.S.",
                    "email": "contacto@techsolutions.com.co",
                    "phone": "+57-1-123-4567",
                },
                "branches": [
                    {
                        "city": "Bogotá",
                        "branch_name": "Sucursal Bogotá",
                        "address": "Calle 100 #15-30, Zona Rosa",
                        "phone": "+57-1-234-5679",
                        "manager": "Juan Pérez",
                        "services": [
                            {
                                "service_name": "Desarrollo de Software",
                                "price": 200000.0
                            },
                            {
                                "service_name": "Consultoría IT",
                                "price": 150000.0
                            }
                        ]
                    },
                    {
                        "city": "Medellín",
                        "branch_name": "Sucursal Medellín",
                        "address": "Carrera 43A #1-50, El Poblado",
                        "phone": "+57-4-456-7890",
                        "manager": "María García",
                        "services": [
                            {
                                "service_name": "Desarrollo de Software",
                                "price": 220000.0
                            },
                            {
                                "service_name": "Consultoría IT",
                                "price": 180000.0
                            }
                        ]
                    }
                ]
            }
        }