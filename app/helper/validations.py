from typing import List
from app.entities.provider import Provider, Company, Branch, Service
from decimal import Decimal

class Validation:
    def validate_provider_data(self, provider: Provider) -> List[str]:
        """
        Validate provider data before saving and return a list of errors
        If no errors, return an empty list
        """
        errors = []
        
        errors.extend(self._validate_company_data(provider.company))
        errors.extend(self._validate_branch_data(provider.branches))        
        
        return errors
    def _validate_company_data(self, company: Company) -> List[str]:
        """
        Validate company data before saving and return a list of errors
        If no errors, return an empty list
        """
        errors = []
        
        if not company.company_id:
            errors.append("CompanyID es requerido")
        if not company.company_name:
            errors.append("Nombre de la empresa es requerido")
        if not company.email:
            errors.append("Email es requerido")
        if not company.phone:
            errors.append("Teléfono es requerido")
        if not company.address:
            errors.append("Dirección es requerida")
        
        return errors
    def _validate_branch_data(self, branches: List[Branch]) -> List[str]:
        """
        Validate branch data before saving and return a list of errors
        If no errors, return an empty list
        """
        if not branches:
            return ["Al menos una sucursal es requerida"]
        
        errors = []
        for i, branch in enumerate(branches):
            branch_errors = self._validate_single_branch(branch, i + 1)
            errors.extend(branch_errors)
        
        return errors

    def _validate_single_branch(self, branch: Branch, branch_number: int) -> List[str]:
        """
        Validate a single branch and return list of errors
        """
        errors = []
        
        # Validate required fields
        errors.extend(self._validate_required_fields(branch, branch_number))
        
        # Validate manager field
        errors.extend(self._validate_manager_field(branch, branch_number))
        
        # Validate services
        errors.extend(self._validate_branch_services(branch, branch_number))
        
        return errors

    def _validate_required_fields(self, branch: Branch, branch_number: int) -> List[str]:
        """
        Validate required fields for a branch
        """
        errors = []
        required_fields = {
            'city': 'Ciudad',
            'address': 'Dirección', 
            'phone': 'Teléfono',
            'branch_name': 'Nombre de sucursal'
        }
        
        for field, field_name in required_fields.items():
            if not getattr(branch, field, None):
                errors.append(f"{field_name} es requerida para sucursal {branch_number}")
        
        return errors

    def _validate_manager_field(self, branch: Branch, branch_number: int) -> List[str]:
        """
        Validate manager field for a branch
        """
        if branch.manager and not isinstance(branch.manager, str):
            return [f"Manager debe ser un string para sucursal {branch_number}"]
        return []

    def _validate_branch_services(self, branch: Branch, branch_number: int) -> List[str]:
        """
        Validate services for a branch
        """
        errors = []
        
        if not hasattr(branch, 'services') or not branch.services:
            errors.append(f"Al menos un servicio es requerido para sucursal {branch_number}")
        else:
            errors.extend(self._validate_service_data(branch.services))
        
        return errors
    def _validate_service_data(self, services: List[Service]) -> List[str]:
        """
        Validate service data before saving and return a list of errors
        If no errors, return an empty list
        """
        errors = []

        if not services:
            errors.append("Al menos un servicio es requerido")
        else:
            for i, service in enumerate(services):
                if not service.service_name:
                    errors.append(f"Nombre de servicio es requerido para servicio {i+1}")
                if not service.price:
                    errors.append(f"Precio es requerido para servicio {i+1}")
                if not isinstance(service.price, (Decimal, float, int)):
                    errors.append(f"Precio debe ser un número para servicio {i+1}")

        return errors
