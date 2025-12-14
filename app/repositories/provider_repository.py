from typing import List, Dict, Any, cast
from concurrent.futures import ThreadPoolExecutor, as_completed
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
from app.repositories.connetion import DynamoConnection
from app.core.exception import BatchWriteException, GetProviderByIdException, SearchByServiceAndCityException, ProviderNotFoundException, CompanyNotUpdateException, GetCompanyException, GetBranchByIdException, DeleteProviderException

class ProviderRepository:
    def __init__(self) -> None:

        self.dynamo_connection = DynamoConnection()

    def execute_batch_write(self, items: List[Dict[str, Any]]) -> None:
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
                response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=cast(Dict[str, Any], request_items))

                # Manejar items no procesados (si los hay)
                unprocessed = response.get('UnprocessedItems', {})
                while unprocessed:
                    print(f"Reintentando {len(unprocessed.get(self.dynamo_connection.table_name, []))} items no procesados...")
                    response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=unprocessed)
                    unprocessed = response.get('UnprocessedItems', {})

            except Exception as e:
                print(f"Error en batch write: {e}")
                raise BatchWriteException(f"Error escribiendo lote de datos: {e}") from e

    # ==================== MÉTODOS DE CONSULTA ====================

    def get_provider_by_id(self, company_id: str) -> List[Dict[str, Any]]:
        """
        Get a complete supplier with all their information
        """
        try:
            response = self.dynamo_connection.table.query(
                KeyConditionExpression=Key('company_id').eq(company_id)
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
            raise GetProviderByIdException(f"Error obteniendo proveedor: {e}") from e


    def get_company_by_id(self, company_id: str) -> Dict[str, Any]:
        """
        Get a company data by company_id
        """
        try:
            response = self.dynamo_connection.table.get_item(
                Key={
                    'company_id': company_id,
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
            raise GetCompanyException(f"Error obteniendo empresa: {e}") from e

    def _get_single_branch(self, company_id: str, branch_id: str) -> List[Dict[str, Any]]:
        """Helper method to get a single branch using GSI"""
        try:
            response = self.dynamo_connection.table.query(
                IndexName='BranchDataLookup',
                KeyConditionExpression='company_id = :company_id AND branch_id = :branch_id',
                ExpressionAttributeValues={
                    ':company_id': company_id,
                    ':branch_id': branch_id
                }
            )
            return response.get('Items', [])
        except Exception:
            return []

    def get_branches_by_ids(self, branch_data: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Get multiple branches using GSI BranchDataLookup with parallel execution
        branch_data: [{"company_id": "123", "branch_id": "branch_001"}, ...]
        """
        try:
            branches = []
            valid_ids = [(data['company_id'], data['branch_id'])
                        for data in branch_data
                        if data.get('company_id') and data.get('branch_id')]

            if not valid_ids:
                return []

            # Ejecutar consultas en paralelo
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_branch = {executor.submit(self._get_single_branch, company_id, branch_id): (company_id, branch_id)
                                   for company_id, branch_id in valid_ids}

                for future in as_completed(future_to_branch):
                    items = future.result()
                    if items:
                        branches.extend(items)

            return branches

        except Exception as e:
            print(f"Error obteniendo sucursales por IDs: {e}")
            raise GetBranchByIdException(f"Error obteniendo sucursales por IDs: {e}") from e
    # ==================== MÉTODOS DE BÚSQUEDA ====================

    def search_providers_by_service_and_city(self, service_name: str, city: str) -> List[Dict[str, Any]]:
        """
        Search for providers that offer a specific service in a specific city
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
            raise SearchByServiceAndCityException(f"Error buscando proveedores: {e}") from e

    def _is_branch_unique(self, branch_id: str) -> bool:
        """Helper method to check if branch_id is unique"""
        try:
            response = self.dynamo_connection.table.query(
            IndexName='branch_id-index',
            KeyConditionExpression='branch_id = :branch_id',
            ExpressionAttributeValues={
                ':branch_id': branch_id
            },
            Select='COUNT'
            )
            count = response.get('Count', 0)
            return count == 0
        except Exception as e:
            print(f"Error validando branch_id {branch_id}: {e}")
            return False


    def validate_branch_ids_uniqueness(self, branch_ids: List[str]) -> Dict[str, bool]:
        """
        Validates that multiple branch_ids are unique using parallel execution
        Returns a dictionary where non-unique branch_ids (already existing) have the value True
        """
        try:
            non_unique_ids = {}

            if not branch_ids:
                return {}

            # Ejecutar validaciones en paralelo
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_branch = {executor.submit(self._is_branch_unique, branch_id): branch_id
                                    for branch_id in branch_ids}

                for future in as_completed(future_to_branch):
                    branch_id = future_to_branch[future]
                    is_unique = future.result()
                    if not is_unique:
                        non_unique_ids[branch_id] = True

            return non_unique_ids

        except Exception as e:
            print(f"Error validando unicidad de branch_ids: {e}")
            raise GetBranchByIdException(f"Error validando unicidad de branch_ids: {e}") from e

    # ==================== MÉTODOS DE ACTUALIZACIÓN ====================

    def update_company(self, company_id: str, update_expression: str, expression_attribute_values: Dict[str, Any]) -> None:
        try:
            self.dynamo_connection.table.update_item(
                    Key={
                        'company_id': company_id,
                        'SK': '#metadata'
                    },
                    UpdateExpression=update_expression,
                    ExpressionAttributeValues=expression_attribute_values
                )
        except Exception as e:
            print(f"Error actualizando empresa: {e}")
            raise CompanyNotUpdateException(f"Error actualizando empresa: {e}") from e

    def delete_provider(self, company_id: str) -> bool:
        """
        Elimina un proveedor completo y todos sus datos relacionados
        """
        try:
            # Obtener todos los elementos del proveedor
            response = self.dynamo_connection.table.query(
                KeyConditionExpression=Key('company_id').eq(company_id)
            )

            items = response.get('Items', [])
            if not items:
                return False

            # Eliminar en lotes
            delete_requests = []
            for item in items:
                delete_requests.append({
                    'DeleteRequest': {
                        'Key': {'company_id': item['company_id'], 'SK': item['SK']}
                    }
                })

            # Procesar en lotes de 25
            batch_size = 25
            for i in range(0, len(delete_requests), batch_size):
                batch = delete_requests[i:i + batch_size]
                request_items = {self.dynamo_connection.table_name: batch}

                response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=cast(Dict[str, Any], request_items))

                # Manejar items no procesados
                unprocessed = response.get('UnprocessedItems', {})
                while unprocessed:
                    response = self.dynamo_connection.table.meta.client.batch_write_item(RequestItems=unprocessed)
                    unprocessed = response.get('UnprocessedItems', {})

            print(f"Proveedor {company_id} eliminado exitosamente")
            return True

        except ClientError as e:
            raise DeleteProviderException(f"Error eliminando proveedor: {e}") from e
