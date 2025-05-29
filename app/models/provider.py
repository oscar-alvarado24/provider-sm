from pydantic import BaseModel, Field, validator
from typing import List, Optional
import uuid

# Branch Models
class BranchBase(BaseModel):
    name: str = Field(..., example="Main Branch")
    address: str = Field(..., example="123 Main St") # City is now a separate field
    city: str = Field(..., example="Anytown")
    phone: str = Field(..., example="555-123-4567")
    manager_name: str = Field(..., example="Jane Doe")
    email: str = Field(..., example="jane.doe@example.com")

class BranchCreate(BranchBase):
    pass

class Branch(BranchBase):
    # In case we want to add fields later specific to responses, like an ID
    pass

# Provider Models
class ProviderBase(BaseModel):
    name: str = Field(..., example="Tech Solutions Inc.")
    email: str = Field(..., example="contact@techsolutions.com")
    address: str = Field(..., example="456 Corporate Blvd, Anytown, USA") # This will be used for city filtering
    phone: str = Field(..., example="555-987-6543")

class ProviderCreate(ProviderBase):
    services: List[str] = Field(..., min_items=1, example=["Cloud Computing", "Data Analytics"])
    branches: List[BranchCreate] = Field(..., min_items=1)

    @validator('services')
    def services_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Provider must offer at least one service.')
        return v

    @validator('branches')
    def branches_must_not_be_empty(cls, v):
        if not v:
            raise ValueError('Provider must have at least one branch.')
        return v

class ProviderUpdate(BaseModel): # Using BaseModel directly for full flexibility in updates
    name: Optional[str] = Field(None, example="Tech Solutions LLC.")
    email: Optional[str] = Field(None, example="info@techsolutions.com")
    address: Optional[str] = Field(None, example="789 Innovation Dr, Anytown, USA")
    phone: Optional[str] = Field(None, example="555-111-2222")
    services: Optional[List[str]] = Field(None, min_items=1, example=["AI Development"])
    branches: Optional[List[BranchCreate]] = Field(None, min_items=1)

    @validator('services')
    def services_update_must_not_be_empty_if_provided(cls, v):
        if v is not None and not v: # only validate if services is actually provided
            raise ValueError('If services are being updated, the list cannot be empty.')
        return v

    @validator('branches')
    def branches_update_must_not_be_empty_if_provided(cls, v):
        if v is not None and not v: # only validate if branches is actually provided
            raise ValueError('If branches are being updated, the list cannot be empty.')
        return v


class ProviderResponse(ProviderBase):
    id: str = Field(..., example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    services: List[str] = Field(..., example=["Cloud Computing", "Data Analytics"])
    branches: List[Branch] = Field(...)

class ProviderNameResponse(BaseModel):
    id: str = Field(..., example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    name: str = Field(..., example="Tech Solutions Inc.")

class ProviderFilterQueryParams(BaseModel):
    city: str = Field(..., example="Anytown") # This 'city' refers to the branch's city
    service: str = Field(..., example="Cloud Computing")
