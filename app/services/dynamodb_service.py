import os
import uuid
from typing import List, Optional, Dict, Any

from collections import defaultdict

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key
from app.repositories.connetion import DynamoConnection
from app.entities import Company, Branch, Service, Provider
from app.core.exception import CreateProviderException, BatchWriteException, GetProviderByIdException, SearchByServiceAndCityException, ProviderNotFoundException, CompanyNotDeletedException, CompanyNotUpdateException, CompanyNotSaveException, CompanyNotDeleteOrSaveException, SaveProviderException
from app.repositories.provider_repository import ProviderRepository
from app.helper.create_dict_provider import GenerateDictProvider
from app.helper.validations import Validation
from app.helper.create_provider import CreateProvider
class DynamoDBService:
    def __init__(self):
        self.repository = ProviderRepository()
        self.generate_dict_provider = GenerateDictProvider()
        self.validation = Validation()
        self.generate_provider = CreateProvider()

    def create_provider(self, provider: Provider) -> str:
        """
        Create  provider complete (company + branches + services) of transactional form
        """
        try:
            company = provider.company
            branches = provider.branches
            errors = self.validation.validate_provider_data(provider)
            if errors:
                raise ValueError(f"Errores de validación: {', '.join(errors)}")
            provider_save = self.generate_dict_provider.create_dict_provider(company, branches)
            self.repository._execute_batch_write(provider_save)
            return f"Proveedor con id {company.company_id} creado exitosamente"
        except Exception as e:
            print(f"Error creando proveedor: {e}")
            raise CreateProviderException(f"Error creando proveedor: {e}")

    def get_provider_by_id(self, company_id: str) -> Provider:
        """
        Get complete provider by company_id
        """
        try:
            items = self.repository.get_provider_by_id(company_id)
            return self.generate_provider.create_provider_from_dict(items)
        except Exception as e:
            if isinstance(e, ProviderNotFoundException):
                raise e
            print(f"Error obteniendo proveedor por ID: {e}")
            raise GetProviderByIdException(f"Error obteniendo proveedor por ID: {e}")

    def update_company(self, company_id: str, update_company: Company) -> str:
        """
        Update company information
        """
        try:
            self.repository.get_company_by_id(company_id)
            
            update_data = {k: v for k, v in update_company.__dict__.items() if v is not None and k != 'company_id'}
            if not update_data:
                return "No hay datos para actualizar."
            update_expression = "SET " + ", ".join(f"{k} = :{k}" for k in update_data.keys())
            expression_attribute_values = {f":{k}": v for k, v in update_data.items()}
            self.repository.update_company(company_id, update_expression, expression_attribute_values)
            return f"Empresa con id {company_id} actualizada exitosamente"
        except Exception as e:
            if isinstance(e, ProviderNotFoundException or CompanyNotUpdateException):
                raise e
            print(f"Error actualizando empresa: {e}")
            raise CompanyNotUpdateException(f"Error actualizando empresa: {e}")