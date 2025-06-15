import os
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import defaultdict

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key
from dataclasses import asdict
from app.models.provider import Company, Branch, Service, Provider
from app.models.request_models import ProviderRequest
from app.models.response_models import ProviderDetailResponse, ProviderResponse,BranchResponse, BranchWithoutServicesResponse, CompanyResponse, CompanyNameResponse, ServiceResponse
from app.exception import CreateProviderException, BatchWriteException, GetProviderByIdException, SearchByServiceAndCityException, ProviderNotFoundException, CompanyNotDeletedException, CompanyNotUpdateException, CompanyNotSaveException, CompanyNotDeleteOrSaveException, SaveProviderException



class DynamoDBService:
    def __init__(self, region_name: Optional[str] = None, endpoint_url: Optional[str] = None):
        self.rechard_variables()
        self.table_name = os.getenv('DYNAMODB_TABLE_NAME')
        print("Nombre de tabla al inicializar:", self.table_name)
        self.region_name = region_name
        self.endpoint_url = endpoint_url

        dynamodb_args = {}
        if self.region_name:
            dynamodb_args['region_name'] = self.region_name
        if self.endpoint_url:
            dynamodb_args['endpoint_url'] = self.endpoint_url
        
        # Configuración de credenciales mejorada
        self._configure_credentials(dynamodb_args)

        try:

            print(f"Initializing DynamoDBService with table: {self.table_name}, region: {self.region_name}, endpoint: {self.endpoint_url}")
            self.dynamodb = boto3.resource('dynamodb', **dynamodb_args)
            self.table = self.dynamodb.Table(self.table_name) # type: ignore
            
            # Verificar la conexión
            self._test_connection()
            
        except ClientError as e:
            print(f"Error de cliente DynamoDB: {e}")
            raise ConnectionError(f"Failed to connect to DynamoDB table '{self.table_name}': {e}")
        except Exception as e:
            print(f"Error inesperado: {e}")
            raise ConnectionError(f"Unexpected error initializing DynamoDBService: {e}")
        
    def rechard_variables(self):
        """
        Recarga las variables de entorno desde el archivo .env
        """
        from dotenv import load_dotenv
        load_dotenv('.env', override=True)
            
    def _configure_credentials(self, dynamodb_args: Dict[str, Any]):
        """Configura las credenciales de AWS de forma robusta"""
        self.rechard_variables()
        # Si es endpoint local (DynamoDB Local), usar credenciales dummy
        if self.endpoint_url and ('localhost' in self.endpoint_url or '127.0.0.1' in self.endpoint_url):
            print("Detected local DynamoDB endpoint, using dummy credentials")
            dynamodb_args['aws_access_key_id'] = 'dummy'
            dynamodb_args['aws_secret_access_key'] = 'dummy'
            return
        
        # Para endpoints reales, verificar credenciales
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        session_token = os.getenv('AWS_SESSION_TOKEN')
        
        print("AWS Credentials check:")
        print(f"- AWS_ACCESS_KEY_ID: {'SET' if access_key else 'NOT SET'}")
        print(f"- AWS_SECRET_ACCESS_KEY: {'SET' if secret_key else 'NOT SET'}")
        print(f"- AWS_SESSION_TOKEN: {'SET' if session_token else 'NOT SET'}")
        
        # Si no hay credenciales configuradas, usar perfil default o IAM role
        if not access_key or not secret_key:
            print("Using default AWS credentials chain (profile, IAM role, etc.)")
            # boto3 usará automáticamente el perfil default o IAM role
            return
        
        # Si hay credenciales explícitas, usarlas
        dynamodb_args['aws_access_key_id'] = access_key
        dynamodb_args['aws_secret_access_key'] = secret_key
        if session_token:
            dynamodb_args['aws_session_token'] = session_token

    def _test_connection(self):
        """Prueba la conexión con DynamoDB"""
        try:
            # Intentar describir la tabla para verificar la conexión
            response = self.table.meta.client.describe_table(TableName=self.table_name)
            print(f"Connection successful! Table status: {response['Table']['TableStatus']}")
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                print(f"WARNING: Table {self.table_name} does not exist")
                raise ConnectionError(f"Table '{self.table_name}' does not exist. Please create it before using the service.")
            else:
                print(f"Connection test failed: {e}")
                raise

    def _get_timestamp(self) -> str:
        """Obtiene timestamp actual"""
        return datetime.now().isoformat()

    def _prepare_company_item(self, company: Company, timestamp: str) -> Dict[str, Any]:
        """Prepara el item de la empresa para DynamoDB"""
        company.created_at = timestamp
        company_dict = asdict(company)
        company_dict.pop('company_id', None)        
        return {
            'CompanyID': f'{company.company_id}',
            'SK': '#metadata',
            'EntityType': 'company',
            'created_at': timestamp,
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
            for service in branch_services:
                service_key = service.service_name.lower().replace(" ", "_")

                item = {
                    'CompanyID': f'{company_id}',
                    'SK': f'city#{branch.city}#{branch.branch_name}#service#{service_key}',  
                    'EntityType': 'branch-service',
                    'GSI1PK': f'service#{service_key}#city#{city}',
                    'company_name': f'{company_name}',
                    **branch_dict,
                    **asdict(service)
                }
                branch_and_services_items.append(item)
        
        return branch_and_services_items


    def create_provider(self, provider: Provider) -> str:
        """
        Create  provider complete (company + branches + services) of transactional form
        """
        try:
            timestamp = self._get_timestamp()
            company = provider.company
            branches = provider.branches
            errors = self._validate_provider_data(provider)
            if errors:
                raise ValueError(f"Errores de validación: {', '.join(errors)}")
            
            self._save_provider(company, branches, timestamp)

            return f"Proveedor con id {company.company_id} creado exitosamente"

        except Exception as e:
            print(f"Error creando proveedor: {e}")
            raise CreateProviderException(f"Error creando proveedor: {e}")

    def _execute_batch_write(self, items: List[Dict[str, Any]]) -> None:
        """
        Ejecuta escritura en lotes de los items a DynamoDB
        DynamoDB permite máximo 25 items por batch
        """
        batch_size = 25
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Preparar el batch request
            request_items = {
                self.table_name: [
                    {'PutRequest': {'Item': item}} for item in batch
                ]
            }
            
            try:
                response = self.table.meta.client.batch_write_item(RequestItems=request_items)
                
                # Manejar items no procesados (si los hay)
                unprocessed = response.get('UnprocessedItems', {})
                while unprocessed:
                    print(f"Reintentando {len(unprocessed.get(self.table_name, []))} items no procesados...")
                    response = self.table.meta.client.batch_write_item(RequestItems=unprocessed)
                    unprocessed = response.get('UnprocessedItems', {})
                    
            except Exception as e:
                print(f"Error en batch write: {e}")
                raise BatchWriteException(f"Error escribiendo lote de datos: {e}")

    # ==================== MÉTODOS DE CONSULTA MEJORADOS ====================
    
    def get_provider_by_id(self, company_id: str) -> Optional[ProviderDetailResponse]:
        """
        Obtiene un proveedor completo con toda su información
        """
        try:
            response = self.table.query(
                KeyConditionExpression=Key('CompanyID').eq(company_id)
            )
            
            items = response.get('Items', [])
            if not items:
                raise ProviderNotFoundException(f"No se encontró el proveedor con ID: {company_id}")
            print(f"provider found:'{items}")
            # Separar items por tipo
            branches_data = []
            branch_processed = set()
            services: defaultdict[str, List[ServiceResponse]] = defaultdict(list)
            company = None  
            
            for item in items:
                if item['SK'] == '#metadata':
                    print(f"company found:'{item}")
                    company = CompanyResponse(
                        company_id=item['CompanyID'],
                        company_name=item['company_name'],
                        email=item['email'],
                        phone=item['phone'],
                        created_at=item.get('created_at'),
                        address=item['address']
                    )
                else:
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
                        branches_data.append(BranchResponse(**branch))
                        branch_processed.add(item['branch_name'])
                    print(f"service found:'{item}")
                    service = {
                        'service_name': item['service_name'],
                        'price': item['price']
                    }
                    services[item['branch_name']].append(ServiceResponse(**service))
            for branch in branches_data:
                    branch.services = services[branch.branch_name]
            
            if company is None:
                raise ProviderNotFoundException("No se encontró información de la empresa para el proveedor solicitado.")
            
            return ProviderDetailResponse(
                company=company,
                branches=branches_data
            )
            
        except Exception as e:
            if isinstance(e, ProviderNotFoundException):
                raise e
            print(f"Error obteniendo proveedor: {e}")
            raise GetProviderByIdException(f"Error obteniendo proveedor: {e}")

    

    # ==================== MÉTODOS DE BÚSQUEDA ====================
    
    def search_providers_by_service_and_city(self, service_name: str, city: str) -> List[ProviderResponse ]:
        """
        Busca proveedores que ofrecen un servicio específico en una ciudad específica
        """
        service_key = service_name.lower().replace(" ", "_")
        city_key = city.lower()
        
        try:
            response = self.table.query(
                IndexName='ServiceCityLookup',
                KeyConditionExpression='GSI1PK = :gsi1pk',
                ExpressionAttributeValues={
                    ':gsi1pk': f'service#{service_key}#city#{city_key}'
                }
            )
            
            print(f"the response is: {response}")
            providers: defaultdict[str, List[BranchWithoutServicesResponse]] = defaultdict(list)
            for item in response.get('Items', []):
                print(f"the item is: {item}")
                branch = {
                    'branch_name': item['branch_name'],
                    'address': item['address'],
                    'phone': item['phone'],
                    'manager': item.get('manager')
                }
                print(f"branch found: {branch}")
                providers[item['company_name']].append(BranchWithoutServicesResponse(**branch))
                print(f"providers: {providers}")
            providers_response = [
                ProviderResponse(
                    company=CompanyNameResponse(name=company_name),
                    branches=branches_list
                )
                for company_name, branches_list in providers.items()
                ]
            return providers_response
            
        except Exception as e:
            raise SearchByServiceAndCityException(f"Error buscando proveedores: {e}")

    # ==================== MÉTODOS DE ACTUALIZACIÓN ====================
    
    def update_company_provider(self, company_id: str, updated_company: Company) -> str:
        """
        Actualiza un proveedor completo (reemplaza toda la información)
        """
        try:
            company=self.get_company(company_id, '#metadata')
            
            if not company:
                raise ProviderNotFoundException(f"Proveedor con ID {company_id} no encontrado")
            updated_company.created_at = company.created_at if updated_company.created_at else self._get_timestamp()
            if updated_company.company_name == company.company_name and updated_company.company_id == company.company_id :
                print(f"Actualizando solo la empresa con ID {company_id}")
                return self._update_only_company(updated_company.company_id, updated_company,company,'#metadata',0)
            else:
                print(f"Actualizando proveedor con ID {company_id}")
                return self._update_company_and_branches(updated_company.company_id, updated_company, company)
            
            
        except Exception as e:
            raise Exception(f"Error actualizando proveedor: {e}")

    def delete_provider(self, company_id: str) -> bool:
        """
        Elimina un proveedor completo y todos sus datos relacionados
        """
        try:
            # Obtener todos los elementos del proveedor
            response = self.table.query(
                KeyConditionExpression=Key('CompanyID').eq(company_id)
            )
            
            items = response.get('Items', [])
            if not items:
                return False
            
            # Eliminar en lotes
            delete_requests = []
            for item in items:
                delete_requests.append({
                    'DeleteRequest': {
                        'Key': {'CompanyID': item['CompanyID'], 'SK': item['SK']}
                    }
                })
            
            # Procesar en lotes de 25
            batch_size = 25
            for i in range(0, len(delete_requests), batch_size):
                batch = delete_requests[i:i + batch_size]
                request_items = {self.table_name: batch}
                
                response = self.table.meta.client.batch_write_item(RequestItems=request_items)
                
                # Manejar items no procesados
                unprocessed = response.get('UnprocessedItems', {})
                while unprocessed:
                    response = self.table.meta.client.batch_write_item(RequestItems=unprocessed)
                    unprocessed = response.get('UnprocessedItems', {})
            
            print(f"Proveedor {company_id} eliminado exitosamente")
            return True
            
        except ClientError as e:
            raise Exception(f"Error eliminando proveedor: {e}")

    # ==================== MÉTODOS DE UTILIDAD ====================
    
    def _validate_provider_data(self, provider: Provider) -> List[str]:
        """
        Validate provider data before saving and return a list of errors
        If no errors, return an empty list
        """
        errors = []
        
        errors.extend(self._validate_company_data(provider.company))
        
        
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
                if not isinstance(service.price, (int, float)):
                    errors.append(f"Precio debe ser un número para servicio {i+1}")

        return errors

    def _save_provider(self, company: Company, branches: List[Branch], timestamp: str) -> None:
            try:
                print(f"Proceso de guardando proveedor: {company.company_name}")
                # Prepare all items to write
                all_items = []

                # 1. Prepare company item 
                company_item = self._prepare_company_item(company, timestamp)
                all_items.append(company_item)

                # 2. Prepare branch items 
                branch_items = self._prepare_branch_and_services_items(company.company_id,company.company_name, branches)
                all_items.extend(branch_items)

                # 3. Execute transaction to create all items
                self._execute_batch_write(all_items)
            except Exception as e:
                print(f"Error guardando proveedor: {e}")
                raise SaveProviderException(f"Error guardando proveedor: {e}")
    def get_company(self, company_id: str, sk: str) -> Optional[Company]:
        """
        Obtiene un registro específico por CompanyID (PK) y SK
        """
        try:
            print(f"Obteniendo empresa con CompanyID: {company_id} y SK: {sk}")
            response = self.table.get_item(
                Key={
                    'CompanyID': company_id,
                    'SK': sk
                }
            )
            
            return Company(
                company_id=company_id,
                company_name=response['Item']['company_name'],
                email=response['Item']['email'],
                phone=response['Item']['phone'],
                created_at=response['Item'].get('created_at'),
                address=response['Item']['address']
            )
            
        except ClientError as e:
            print(f"Error obteniendo registro por PK y SK: {e}")
            raise Exception(f"Error obteniendo registro por PK y SK: {e}")
   
    
    
    def delete_company(self, company_id: str, sk: str) -> bool:
        """
        Elimina un registro específico por CompanyID (PK) y SK
        """
        try:
            response = self.table.delete_item(
                Key={
                    'CompanyID': company_id,
                    'SK': sk
                },
                ReturnValues='ALL_OLD'
            )
            
            # Verificar si se eliminó algo
            return 'Attributes' in response
            
        except ClientError as e:
            print(f"Error eliminando registro: {e}")
            raise Exception(f"Error eliminando registro: {e}")
        
    def _update_only_company(self, company_id: str, updated_company: Company, old_company: Company, sk: str, retry:int) -> str:
        """
        Actualiza solo la información de la empresa (sin eliminar sucursales ni servicios)
        """
        try:
            process_update = self._delete_and_save_company(company_id, updated_company, sk)
            while process_update is False and retry < 3:
                print(f"Intentando eliminar proveedor {company_id} (intento {retry})")
                process_update = self._delete_and_save_company(company_id, updated_company, sk)
                retry += 1
            if process_update:
                return f"Proveedor con id {company_id} actualizado exitosamente"
            else:
                raise CompanyNotDeletedException(f"Proveedor con ID {company_id} no pudo ser eliminado")
        except Exception as e:
            if isinstance(e, CompanyNotDeletedException) or isinstance(e, CompanyNotSaveException) or isinstance(e, CompanyNotDeleteOrSaveException):   
                raise e
            else:
                print(f"Error actualizando proveedor: {e}")
                raise CompanyNotUpdateException(f"Error : {e}")
            
    def _delete_and_save_company(self, company_id: str, updated_company: Company, sk: str) -> bool:
        """
        Delete old company and save the updated company
        """
        try:
            try:
                delete_company = self.delete_company(company_id, sk)
            except Exception as e:
                print(f"Error eliminando proveedor: {e}")
                raise CompanyNotDeletedException(f"Error : {e}")
            if delete_company:
                company_save = self._prepare_company_item(updated_company, updated_company.created_at if updated_company.created_at is not None else self._get_timestamp())
                try:
                    self.table.put_item(Item=company_save)
                    return True
                except Exception as e:
                    print(f"Error guardando proveedor: {e}")
                    raise CompanyNotSaveException(f"Error : {e}")
            else:
                return False
        except Exception as e:
            if isinstance(e, CompanyNotDeletedException ) or isinstance(e, CompanyNotSaveException):
                raise e
            else:
                print(f"Error: {e}")
                raise CompanyNotDeleteOrSaveException(f"Error : {e}")
    def _update_company_and_branches(self, company_id: str, updated_company: Company, old_company: Company) -> str:
        """
        Update data of company and branches becouse company_id or company_name is not the same
        """
        try:
            provider= self.table.query(
                KeyConditionExpression=Key('CompanyID').eq(company_id)
            )
            if not provider:
                raise ProviderNotFoundException(f"Proveedor con ID {company_id} no encontrado")
            attempts = 0
            while attempts < 3:
                delete_provider = self.delete_provider(company_id)
                if delete_provider:
                    attempts_save = 0
                    while attempts_save < 3:
                        print("provider eliminado, guardando proveedor actualizado")
                        print(f"provider eliminado: {provider}" )
                        save_provider_process = self._save_provider_update(updated_company, old_company, provider)
                        if isinstance(save_provider_process, str):
                            return save_provider_process
                        attempts_save += 1
                    raise CompanyNotSaveException(f"Proveedor con ID {company_id} no pudo ser guardado")
                attempts += 1
                print(f"retrying to save provider {company_id} (attempt {attempts})")
            raise CompanyNotDeletedException(f"Proveedor con ID {company_id} no pudo ser eliminado")
        except Exception as e:
            if isinstance(e, CompanyNotDeletedException) or isinstance(e, CompanyNotSaveException) or isinstance(e, CompanyNotDeleteOrSaveException):
                raise e
            else:
                print(f"Error actualizando proveedor: {e}")
                raise CompanyNotUpdateException(f"Error : {e}")
    
    def _save_provider_update(self, updated_company: Company, old_company: Company, provider: Provider) -> str|bool:
        """
        Save provider update
        """
        
        print(f"ingresando al metodo _save_provider_update")
        try:
            if not provider.branches:
                print(f"No se encontraron sucursales para el proveedor con ID {updated_company.company_id}")
            
            print(f"guardando proveedor actualizado: {updated_company} y sus sucursales: {provider.branches}")
            self._save_provider(updated_company, provider.branches, old_company.created_at if old_company.created_at is not None else self._get_timestamp())
            company_saved=self.get_company(updated_company.company_id, '#metadata')
            if company_saved:
                return f"Proveedor con id {updated_company.company_id} actualizado exitosamente"
            else:
                return False
        except Exception as e:
            print(f"Error guardando proveedor actualizado: {e}")
            raise SaveProviderException(f"Error guardando proveedor: {e}")