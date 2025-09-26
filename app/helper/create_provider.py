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
                        company_id=item['CompanyID'],
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
                            'branch_name': item['branch_name'],
                            'city': item['city'],
                            'address': item['address'],
                            'phone': item['phone'],
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