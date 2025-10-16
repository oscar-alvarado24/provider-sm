from typing import List, Dict, Any
from collections import defaultdict
from app.entities.provider import Provider, Company, Branch, Service
from app.core.exception import ProviderNotFoundException, CreateObjectProviderException
class CreateProvider:
    def create_provider_from_dict(self, provider_dict: List[Dict[str, Any]]) -> Provider:
        """
        Create a provider dictionary for DynamoDB
        """
        try:
            branches_data = []
            branch_processed = set()
            services: defaultdict[str, List[Service]] = defaultdict(list)
            company = None  
            
            for item in provider_dict:
                print(f"Processing item: {item}")
                if item['EntityType'] == 'company':
                    print(f"company found:'{item}")
                    company = Company(
                        company_id=item['company_id'],
                        company_name=item['company_name'],
                        email=item['email'],
                        phone=item['phone'],
                        created_at=item.get('created_at'),
                        address=item['address']
                    )
                elif item['EntityType'] == 'branch':
                    if item['branch_name'] not in branch_processed:
                        print(f"branch found:'{item}")
                        branch={
                            'branch_id': item['branch_id'],
                            'branch_name': item['branch_name'],
                            'city': item['city'],
                            'address': item['address'],
                            'phone': item['phone'],
                            'email': item['email'],
                            'manager': item.get('manager'),
                            'services': []
                        }
                        branches_data.append(Branch(**branch))
                        branch_processed.add(item['branch_name'])
                else:
                    print(f"service found:'{item}")
                    service = {
                        'service_name': item['service_name'],
                        'price': item['price']
                    }
                    parts = item['SK'].split('#')
                    branch_name = parts[2]
                    services[branch_name].append(Service(**service))
            for branch in branches_data:
                    branch.services = services[branch.branch_name]
            
            if company is None:
                raise ProviderNotFoundException("No se encontró información de la empresa para el proveedor solicitado.")
            
            return Provider(
                company=company,
                branches=branches_data
            )
        except Exception as e:
            print(f"Error al crear el proveedor: {e}")
            raise CreateObjectProviderException(f"Error al crear el proveedor: {str(e)}")
    
    def create_branch_without_services_from_dict(self, branch_dict: Dict[str, Any]) -> Branch:
        """
        Create a branch object from a dictionary
        """
        try:
            branch = Branch(
                branch_id=branch_dict['branch_id'],
                branch_name=branch_dict['branch_name'],
                city=branch_dict['city'],
                address=branch_dict['address'],
                phone=branch_dict['phone'],
                email=branch_dict['email'],
                manager=branch_dict['manager'],
                services=[],
                updated_at=branch_dict.get('updated_at')
            )
            return branch
        except Exception as e:
            print(f"Error al crear la sucursal: {e}")
            raise CreateObjectProviderException(f"Error al crear la sucursal: {str(e)}")
        
    def create_branches_from_dict_list(self, branches_list: List[Dict[str, Any]]) -> List[Branch]:
        """
        Create multiple branch objects from a list of dictionaries
        """
        branches = []
        errors = []
        
        for index, branch_dict in enumerate(branches_list):
            try:
                branch = self.create_branch_without_services_from_dict(branch_dict)
                branches.append(branch)
            except Exception as e:
                errors.append(f"Error en sucursal índice {index}: {str(e)}")
        
        if errors:
            error_message = "; ".join(errors)
            raise CreateObjectProviderException(f"Errores al crear sucursales: {error_message}")
        
        return branches