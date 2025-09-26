from typing import  Optional
from decimal import Decimal

from dataclasses import dataclass

@dataclass
class Company:
    company_id: str
    address: str
    company_name: str
    email: str
    phone: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@dataclass
class Service:
    service_name: str
    price: Decimal
    updated_at: Optional[str] = None

@dataclass
class Branch:
    branch_name: str
    city: str
    address: str
    phone: str
    email: str
    manager: str
    services: list[Service]
    updated_at: Optional[str] = None

@dataclass
class Provider:
    company: Company
    branches: list[Branch]