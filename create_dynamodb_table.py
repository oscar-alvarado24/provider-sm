import boto3
import os
from botocore.exceptions import ClientError
from typing import Optional

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Variables de entorno cargadas desde .env")
    
    # Debug: mostrar lo que se cargó
    print("🔍 Debug - Variables cargadas:")
    print(f"   • DYNAMODB_TABLE_NAME: '{os.getenv('DYNAMODB_TABLE_NAME')}'")
    print(f"   • DYNAMODB_ENDPOINT_URL: '{os.getenv('DYNAMODB_ENDPOINT_URL')}'")
    print(f"   • AWS_ACCESS_KEY_ID: '{os.getenv('AWS_ACCESS_KEY_ID')}'")
    
except ImportError:
    print("⚠️  python-dotenv no está instalado. Usando variables de entorno del sistema.")
    print("   Para instalar: pip install python-dotenv")
    print("🔍 Debug - Variables del sistema:")
    print(f"   • DYNAMODB_TABLE_NAME: '{os.getenv('DYNAMODB_TABLE_NAME')}'")
    print(f"   • DYNAMODB_ENDPOINT_URL: '{os.getenv('DYNAMODB_ENDPOINT_URL')}'")
    print(f"   • AWS_ACCESS_KEY_ID: '{os.getenv('AWS_ACCESS_KEY_ID')}'")
except Exception as e:
    print(f"❌ Error cargando .env: {e}")
    print("🔍 Debug - Variables del sistema:")
    print(f"   • DYNAMODB_TABLE_NAME: '{os.getenv('DYNAMODB_TABLE_NAME')}'")
    print(f"   • DYNAMODB_ENDPOINT_URL: '{os.getenv('DYNAMODB_ENDPOINT_URL')}'")
    print(f"   • AWS_ACCESS_KEY_ID: '{os.getenv('AWS_ACCESS_KEY_ID')}'")

print("")  # Línea en blanco

class DynamoDBTableCreator:
    def __init__(self, region_name: Optional[str] = None, endpoint_url: Optional[str] = None):
        """
        Inicializa el creador de tablas DynamoDB
        
        Args:
            region_name: Región de AWS (ej: 'us-east-1', 'us-west-2')
            endpoint_url: URL del endpoint (para DynamoDB local usar 'http://localhost:8000')
        """
        self.region_name = region_name or os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
        self.endpoint_url = endpoint_url
        
        # Verificar y mostrar credenciales
        self._check_credentials()
        
        dynamodb_args = {'region_name': self.region_name}
        
        # Configurar credenciales
        if self.endpoint_url and ('localhost' in self.endpoint_url or '127.0.0.1' in self.endpoint_url):
            print("🔧 Usando DynamoDB Local con credenciales dummy")
            dynamodb_args['endpoint_url'] = self.endpoint_url
            dynamodb_args['aws_access_key_id'] = 'dummy'
            dynamodb_args['aws_secret_access_key'] = 'dummy'
        elif self.endpoint_url:
            dynamodb_args['endpoint_url'] = self.endpoint_url
        
        try:
            self.dynamodb = boto3.client('dynamodb', **dynamodb_args)
            print(f"✅ Cliente DynamoDB inicializado - Región: {self.region_name}")
            if self.endpoint_url:
                print(f"🔗 Endpoint: {self.endpoint_url}")
        except Exception as e:
            print(f"❌ Error inicializando cliente DynamoDB: {e}")
            raise

    def _check_credentials(self):
        """Verifica y muestra el estado de las credenciales AWS"""
        print("\n🔐 Verificando credenciales AWS...")
        
        # Verificar variables de entorno
        access_key = os.getenv('AWS_ACCESS_KEY_ID')
        secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        session_token = os.getenv('AWS_SESSION_TOKEN')
        region = os.getenv('AWS_DEFAULT_REGION')
        profile = os.getenv('AWS_PROFILE')
        
        print(f"   • AWS_ACCESS_KEY_ID: {'✅ Configurado' if access_key else '❌ No configurado'}")
        print(f"   • AWS_SECRET_ACCESS_KEY: {'✅ Configurado' if secret_key else '❌ No configurado'}")
        print(f"   • AWS_SESSION_TOKEN: {'✅ Configurado' if session_token else '❌ No configurado'}")
        print(f"   • AWS_DEFAULT_REGION: {region or '❌ No configurado'}")
        print(f"   • AWS_PROFILE: {profile or '❌ No configurado'}")
        
        # Intentar obtener credenciales usando boto3
        try:
            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials:
                print(f"   • Credenciales boto3: ✅ Encontradas")
                print(f"   • Método de credenciales: {type(credentials).__name__}")
            else:
                print(f"   • Credenciales boto3: ❌ No encontradas")
        except Exception as e:
            print(f"   • Error obteniendo credenciales: {e}")
        
        # Verificar credenciales inválidas comunes
        if access_key and ('=' in access_key or '+' in access_key or '/' in access_key):
            if not access_key.replace('=', '').replace('+', '').replace('/', '').isalnum():
                print("   ⚠️  WARNING: AWS_ACCESS_KEY_ID contiene caracteres que podrían causar problemas")
        
        print("") # Línea en blanco para separar

    def create_providers_table(self, table_name: str = 'Suppliers') -> bool:
        """
        Crea la tabla de proveedores con su GSI
        
        Args:
            table_name: Nombre de la tabla a crear
            
        Returns:
            bool: True si la tabla se creó exitosamente
        """
        try:
            print(f"🚀 Creando tabla '{table_name}'...")
            
            table_definition = {
                'TableName': table_name,
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'CompanyID',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'SK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'GSI1PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'company_name',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'service_name',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'CompanyID',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'SK',
                        'KeyType': 'RANGE'
                    }
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'ServiceCityLookup',
                        'KeySchema': [
                            {
                                'AttributeName': 'GSI1PK',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'service_name',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'INCLUDE',
                            'NonKeyAttributes': ['manager', 'branch_name', 'address', 'phone']
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 1,
                            'WriteCapacityUnits': 1
                        }
                    },
                    {
                        'IndexName': 'BranchServiceLookup',
                        'KeySchema': [
                            {
                                'AttributeName': 'SK',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'service_name',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL' 
                        },
                        'ProvisionedThroughput': {
                            'ReadCapacityUnits': 1,
                            'WriteCapacityUnits': 1
                        }
                    }
                ],
                'BillingMode': 'PROVISIONED',
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 2,
                    'WriteCapacityUnits': 2
                }
            }
            
            response = self.dynamodb.create_table(**table_definition)
            
            print(f"✅ Tabla '{table_name}' creada exitosamente!")
            print(f"📊 ARN de la tabla: {response['TableDescription']['TableArn']}")
            
            # Esperar a que la tabla esté activa
            print("⏳ Esperando a que la tabla esté activa...")
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(
                TableName=table_name,
                WaiterConfig={
                    'Delay': 2,
                    'MaxAttempts': 30
                }
            )
            
            print("🎉 ¡Tabla activa y lista para usar!")
            
            # Mostrar información de la tabla
            self._show_table_info(table_name)
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ResourceInUseException':
                print(f"⚠️  La tabla '{table_name}' ya existe")
                self._show_table_info(table_name)
                return True
            else:
                print(f"❌ Error creando la tabla: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Error inesperado: {e}")
            return False

    def create_on_demand_table(self, table_name: str = 'Suppliers') -> bool:
        """
        Crea la tabla con facturación bajo demanda (pay-per-request)
        Recomendado para cargas de trabajo impredecibles
        """
        try:
            print(f"🚀 Creando tabla '{table_name}' con facturación bajo demanda...")
            
            table_definition = {
                'TableName': table_name,
                'AttributeDefinitions': [
                    {
                        'AttributeName': 'PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'SK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'GSI1PK',
                        'AttributeType': 'S'
                    },
                    {
                        'AttributeName': 'GSI1SK',
                        'AttributeType': 'S'
                    }
                ],
                'KeySchema': [
                    {
                        'AttributeName': 'PK',
                        'KeyType': 'HASH'
                    },
                    {
                        'AttributeName': 'SK',
                        'KeyType': 'RANGE'
                    }
                ],
                'GlobalSecondaryIndexes': [
                    {
                        'IndexName': 'ServiceCityLookup',
                        'KeySchema': [
                            {
                                'AttributeName': 'GSI1PK',
                                'KeyType': 'HASH'
                            },
                            {
                                'AttributeName': 'GSI1SK',
                                'KeyType': 'RANGE'
                            }
                        ],
                        'Projection': {
                            'ProjectionType': 'ALL'
                        }
                    }
                ],
                'BillingMode': 'PAY_PER_REQUEST'
            }
            
            response = self.dynamodb.create_table(**table_definition)
            
            print(f"✅ Tabla '{table_name}' creada exitosamente con facturación bajo demanda!")
            print(f"📊 ARN de la tabla: {response['TableDescription']['TableArn']}")
            
            # Esperar a que la tabla esté activa
            print("⏳ Esperando a que la tabla esté activa...")
            waiter = self.dynamodb.get_waiter('table_exists')
            waiter.wait(TableName=table_name)
            
            print("🎉 ¡Tabla activa y lista para usar!")
            self._show_table_info(table_name)
            
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            
            if error_code == 'ResourceInUseException':
                print(f"⚠️  La tabla '{table_name}' ya existe")
                self._show_table_info(table_name)
                return True
            else:
                print(f"❌ Error creando la tabla: {e}")
                return False

    def _show_table_info(self, table_name: str):
        """Muestra información detallada de la tabla"""
        try:
            response = self.dynamodb.describe_table(TableName=table_name)
            table = response['Table']
            
            print(f"\n📋 Información de la tabla '{table_name}':")
            print(f"   • Estado: {table['TableStatus']}")
            print(f"   • Elementos: {table.get('ItemCount', 'N/A')}")
            print(f"   • Tamaño: {table.get('TableSizeBytes', 0)} bytes")
            print(f"   • Modo de facturación: {table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')}")
            
            # Información de throughput si es provisioned
            if 'ProvisionedThroughput' in table:
                pt = table['ProvisionedThroughput']
                print(f"   • Capacidad de lectura: {pt['ReadCapacityUnits']} RCU")
                print(f"   • Capacidad de escritura: {pt['WriteCapacityUnits']} WCU")
            
            # Información del GSI
            if 'GlobalSecondaryIndexes' in table:
                for gsi in table['GlobalSecondaryIndexes']:
                    print(f"   • GSI '{gsi['IndexName']}': {gsi['IndexStatus']}")
                    
        except ClientError as e:
            print(f"⚠️  No se pudo obtener información de la tabla: {e}")

    def delete_table(self, table_name: str) -> bool:
        """
        Elimina la tabla (¡CUIDADO! Esta operación es irreversible)
        """
        try:
            print(f"🗑️  Eliminando tabla '{table_name}'...")
            
            # Confirmar eliminación
            confirm = input(f"¿Estás seguro de que quieres eliminar la tabla '{table_name}'? (escribe 'SI' para confirmar): ")
            if confirm != 'SI':
                print("❌ Eliminación cancelada")
                return False
            
            self.dynamodb.delete_table(TableName=table_name)
            
            print(f"✅ Tabla '{table_name}' eliminada exitosamente")
            return True
            
        except ClientError as e:
            print(f"❌ Error eliminando la tabla: {e}")
            return False

    def list_tables(self):
        """Lista todas las tablas disponibles"""
        try:
            response = self.dynamodb.list_tables()
            tables = response.get('TableNames', [])
            
            if tables:
                print("📚 Tablas disponibles:")
                for table in tables:
                    print(f"   • {table}")
            else:
                print("📭 No hay tablas disponibles")
                
        except ClientError as e:
            print(f"❌ Error listando tablas: {e}")


def main():
    """Función principal para crear la tabla"""
    print("🏗️  Creador de Tabla DynamoDB para Proveedores")
    print("=" * 50)
    
    # Configuración desde variables de entorno
    endpoint_url = os.getenv('DYNAMODB_ENDPOINT_URL')  # http://localhost:8000
    region_name = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    
    # Limpiar el nombre de la tabla (remover comentarios y espacios)
    table_name = os.getenv('DYNAMODB_TABLE_NAME', 'Suppliers')
    if table_name:
        # Remover comentarios y espacios extra
        table_name = table_name.split('#')[0].strip()
        # Validar que solo tenga caracteres permitidos
        if not table_name:
            table_name = 'Suppliers'
    
    print(f"📋 Configuración detectada:")
    print(f"   • Endpoint: {endpoint_url or 'AWS DynamoDB'}")
    print(f"   • Región: {region_name}")
    print(f"   • Tabla: '{table_name}'")
    
    # Crear el creador de tablas
    creator = DynamoDBTableCreator(
        region_name=region_name,
        endpoint_url=endpoint_url
    )
    
    # Listar tablas existentes
    print("\n1️⃣  Tablas existentes:")
    creator.list_tables()
    
    # Crear la tabla
    print(f"\n2️⃣  Creando tabla '{table_name}':")
    
    # Opción 1: Tabla con throughput aprovisionado (más económico para cargas predecibles)
    success = creator.create_providers_table(table_name)
    
    # Opción 2: Tabla con facturación bajo demanda (descomenta para usar esta opción)
    # success = creator.create_on_demand_table(table_name)
    
    if success:
        print(f"\n🎉 ¡Tabla '{table_name}' creada y configurada correctamente!")
        print("\n📝 Próximos pasos:")
        print("   1. Actualiza tu aplicación con el nombre de la tabla")
        print("   2. Configura las credenciales de AWS si es necesario")
        print("   3. ¡Comienza a usar tu servicio DynamoDB!")
    else:
        print(f"\n❌ Falló la creación de la tabla '{table_name}'")


if __name__ == "__main__":
    main()