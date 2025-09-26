from dataclasses import asdict
from datetime import datetime
from app.entities.provider import Company, Branch, Service
from typing import List, Dict, Any
class GenerateDictProvider:
    
    def create_dict_provider(self, company: Company, branches: List[Branch]) -> List[Dict[str, Any]]:
        print(f"Proceso de guardando proveedor: {company.company_name}")
        # Prepare all items to write
        all_items = []

        # 1. Prepare company item 
        all_items.append(self._prepare_company_item(company))

        # 2. Prepare branch items 
        all_items.extend(self._prepare_branch_and_services_items(company.company_id, company.company_name, branches))
        return all_items
        
    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual"""
        return datetime.now().isoformat()

    def _prepare_company_item(self, company: Company) -> Dict[str, Any]:
        """Prepara el item de la empresa para DynamoDB"""
        company.created_at = self._get_timestamp()
        company_dict = asdict(company)
        company_dict.pop('company_id', None)        
        return {
            'CompanyID': f'{company.company_id}',
            'SK': '#metadata',
            'EntityType': 'company',
            'created_at': company.created_at,
            **company_dict
        }

    def _prepare_branch_and_services_items(self, company_id: str,company_name: str, branches: List[Branch]) -> List[Dict[str, Any]]:
        """Prepara los items de las sucursales para DynamoDB"""
        branch_and_services_items = []
        
        for branch in branches:
            branch_services = branch.services if hasattr(branch, 'services') else []
            branch_dict = asdict(branch)
            branch_dict.pop('services', None)
            city = branch.city.lower()
            branch_and_services_items.append(self._prepare_branch_items(company_id, branch_dict, branch.branch_name, city))
            for service in branch_services:     
                branch_and_services_items.append(self._prepare_service_item(company_id, branch.branch_name, service, city))
        
        return branch_and_services_items
    
    def _prepare_branch_items(self, company_id: str, branch: Dict[str, Any], branch_name: str, city:str) -> Dict[str, Any]:
        """Prepara el item de la sucursal para DynamoDB"""
    
        return {
            'CompanyID': f'{company_id}',
            'SK': f'city#{city}#{branch_name}',
            'EntityType': 'branch',
            **branch
        }
    
    def _prepare_service_item(self, company_id: str, branch_name: str, service: Service, city:str) -> Dict[str, Any]:
        service_key = service.service_name.lower().replace(" ", "_")
        return {
            'CompanyID': f'{company_id}',
            'SK': f'city#{city}#{branch_name}#service#{service_key}',  
            'EntityType': 'branch-service',
            'GSI1PK': f'service#{service_key}#city#{city}',
            **asdict(service)
        }