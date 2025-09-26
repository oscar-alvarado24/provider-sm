from app.repositories.connetion import DynamoConnection
from typing import List, Optional, Dict, Any
from app.core.exception import BatchWriteException, GetProviderByIdException, SearchByServiceAndCityException, ProviderNotFoundException, CompanyNotDeletedException, CompanyNotUpdateException, CompanyNotSaveException, CompanyNotDeleteOrSaveException, SaveProviderException, GetCompanyException
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

class ProviderRepository:
    def __init__(self) -> None:
        
        self.dynamo_connection = DynamoConnection()

    def _execute_batch_write(self, items: List[Dict[str, Any]]) -> None:
        """
        Runs batch writes of 25 items to DynamoDB at a time
        """
        batch_size = 25
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            
            # Preparar el batch request
            request_items = {
                self.dynamo_connection.table_name: [
                    {'PutRequest': {'Item': item}} for item in batch
                ]
            }
            
            try:
                response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=request_items)
                
                # Manejar items no procesados (si los hay)
                unprocessed = response.get('UnprocessedItems', {})
                while unprocessed:
                    print(f"Reintentando {len(unprocessed.get(self.dynamo_connection.table_name, []))} items no procesados...")
                    response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=unprocessed)
                    unprocessed = response.get('UnprocessedItems', {})
                    
            except Exception as e:
                print(f"Error en batch write: {e}")
                raise BatchWriteException(f"Error escribiendo lote de datos: {e}")

    # ==================== MÉTODOS DE CONSULTA ====================
    
    def get_provider_by_id(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Obtiene un proveedor completo con toda su información
        """
        try:
            response = self.dynamo_connection.table.query(
                KeyConditionExpression=Key('CompanyID').eq(company_id)
            )
            
            items = response.get('Items', [])
            if not items:
                raise ProviderNotFoundException(f"No se encontró el proveedor con ID: {company_id}")
            print(f"provider found:'{items}")
            return items
        except Exception as e:
            if isinstance(e, ProviderNotFoundException):
                raise e
            print(f"Error obteniendo proveedor: {e}")
            raise GetProviderByIdException(f"Error obteniendo proveedor: {e}")

    
    def get_company_by_id(self, company_id: str) -> Dict[str, Any]:
        """
        Get a company data by company_id
        """
        try:
            response = self.dynamo_connection.table.get_item(
                Key={
                    'CompanyID': company_id,
                    'SK': '#metadata'
                }
            )
            item = response.get('Item')
            if not item:
                raise ProviderNotFoundException(f"No se encontró la empresa con ID: {company_id}")
            return item
        except Exception as e:
            if isinstance(e, ProviderNotFoundException):
                raise e
            print(f"Error obteniendo empresa: {e}")
            raise GetCompanyException(f"Error obteniendo empresa: {e}")
    # ==================== MÉTODOS DE BÚSQUEDA ====================
    
    def search_providers_by_service_and_city(self, service_name: str, city: str) -> List[Dict[str, Any]]:
        """
        Busca proveedores que ofrecen un servicio específico en una ciudad específica
        """
        service_key = service_name.lower().replace(" ", "_")
        city_key = city.lower()
        
        try:
            response = self.dynamo_connection.table.query(
                IndexName='ServiceCityLookup',
                KeyConditionExpression='GSI1PK = :gsi1pk',
                ExpressionAttributeValues={
                    ':gsi1pk': f'service#{service_key}#city#{city_key}'
                }
            )
            
            print(f"the response is: {response}")
            items = response.get('Items', [])
            if not items:
                raise ProviderNotFoundException(f"No se encontraron proveedores que ofrezcan '{service_name}' en '{city}'") 
            return items
            
        except Exception as e:
            raise SearchByServiceAndCityException(f"Error buscando proveedores: {e}")

    # ==================== MÉTODOS DE ACTUALIZACIÓN ====================
    
    def update_company(self, company_id: str, update_expression: str, expression_attribute_values: Dict[str, Any]) -> None:
        try:
            self.dynamo_connection.table.update_item(
                    Key={
                        'CompanyID': company_id,
                        'SK': '#metadata'
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values
                )
        except Exception as e:
            print(f"Error actualizando empresa: {e}")
            raise CompanyNotUpdateException(f"Error actualizando empresa: {e}")
        
    def delete_provider(self, company_id: str) -> bool:
        """
        Elimina un proveedor completo y todos sus datos relacionados
        """
        try:
            # Obtener todos los elementos del proveedor
            response = self.dynamo_connection.table.query(
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
                request_items = {self.dynamo_connection.table_name: batch}
                
                response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=request_items)
                
                # Manejar items no procesados
                unprocessed = response.get('UnprocessedItems', {})
                while unprocessed:
                    response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=unprocessed)
                    unprocessed = response.get('UnprocessedItems', {})
            
            print(f"Proveedor {company_id} eliminado exitosamente")
            return True
            
        except ClientError as e:
            raise Exception(f"Error eliminando proveedor: {e}")
