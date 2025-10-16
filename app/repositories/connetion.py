import os
import boto3
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
from botocore.exceptions import ClientError
from typing import Optional
import logging
from app.core.config import settings
from typing import TYPE_CHECKING, TypeAlias

if TYPE_CHECKING:
    from mypy_boto3_dynamodb.service_resource import DynamoDBServiceResource
    DynamoDBResource: TypeAlias = DynamoDBServiceResource
else:
    DynamoDBResource = object
logger = logging.getLogger(__name__)

class DynamoConnection:
    """
    Conexión simple a DynamoDB que adapta su comportamiento según APP_ENV
    Usa if/else simple - sin complicaciones innecesarias
    """
    
    def __init__(
        self,
        table_name: str = settings.dynamodb_table_name or "provider",
        region: str = settings.aws_region or "us-east-1",
        endpoint_url: Optional[str] = settings.dynamodb_endpoint_url,
        access_key_id: Optional[str] = settings.aws_access_key_id,
        secret_access_key: Optional[str] = settings.aws_secret_access_key,
        role_arn: Optional[str] = settings.aws_dynamo_role
    ):
        self.table_name = table_name
        self.region = region
        self.endpoint_url = endpoint_url
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.role_arn = role_arn
        logger.info(f"=== Inicializando conexión a DynamoDB ===")
        logger.info(f"Tabla: {self.table_name}")
        logger.info(f"Región: {self.region}")
        if self.endpoint_url:
            logger.info(f"Endpoint: {self.endpoint_url}")
        if self.role_arn:
            logger.info(f"Rol a asumir: {self.role_arn}")
        
        # Leer el perfil desde variable de entorno
        self.app_env = settings.environment
        
        
        self._refresh_count = 0
        
        # Obtener recurso según el perfil (if/else simple)
        self.dynamodb = self._get_dynamodb_resource()
        self.table = self.dynamodb.Table(table_name)
        
        # Verificar conexión
        self._test_connection()
    
    def _get_dynamodb_resource(self):
        """
        Retorna el recurso DynamoDB según el perfil
        Simple y directo con if/else
        """
        
        # ==========================================
        # LOCAL: DynamoDB Local con credenciales dummy
        # ==========================================
        if self.app_env == 'local':
            logger.info("🔧 Perfil LOCAL: Usando DynamoDB Local")
            
            endpoint = self.endpoint_url or 'http://localhost:8000'
            
            return boto3.resource(
                'dynamodb',
                endpoint_url=endpoint,
                region_name=self.region,
                aws_access_key_id='dummy',
                aws_secret_access_key='dummy'
            )
        
        elif self.app_env == 'prod':
            
            if self.role_arn:
                return self._create_resource_with_assume_role()
            else:
                # Si no hay rol, usar credenciales directas
                logger.warning("⚠️  No hay rol configurado, usando credenciales directas")
                return self._create_resource_with_direct_credentials()
        
        else:
            logger.warning(f"⚠️  Perfil '{self.app_env}' no reconocido, usando configuración por defecto")
            return self._create_resource_with_direct_credentials()
    
    def _create_resource_with_direct_credentials(self):
        """Crear recurso con credenciales directas"""
        dynamodb_args = {}
        if not self.access_key_id or not self.secret_access_key:
            # Si no hay credenciales, dejar que boto3 use la cadena de credenciales
            logger.info("   Usando cadena de credenciales de boto3")
            
        else:
            logger.info(f"   Usando credenciales explícitas: {self.access_key_id[:10]}...")
            dynamodb_args['aws_access_key_id'] = self.access_key_id
            dynamodb_args['aws_secret_access_key'] = self.secret_access_key
        
        if self.endpoint_url:
            dynamodb_args['endpoint_url'] = self.endpoint_url
        
        dynamodb_args['region_name'] = self.region
        return boto3.resource('dynamodb', **dynamodb_args)
        
    def _create_resource_with_assume_role(self):
        """Crear recurso con AssumeRole y auto-refresh"""
        if not self.access_key_id or not self.secret_access_key:
            raise ValueError(
                "AWS_ACCESS_KEY_ID y AWS_SECRET_ACCESS_KEY requeridos "
                "para asumir el rol"
            )
        
        logger.info(f"   Usuario base: {self.access_key_id[:10]}...")
        logger.info(f"   Rol a asumir: {self.role_arn}")
        
        # Crear credenciales renovables
        refreshable_credentials = RefreshableCredentials.create_from_metadata(
            metadata=self._refresh_credentials(),
            refresh_using=self._refresh_credentials,
            method='sts-assume-role'
        )
        
        # Crear sesión con credenciales renovables
        botocore_session = get_session()
        setattr(botocore_session, '_credentials', refreshable_credentials)
        botocore_session.set_config_variable('region', self.region)
        
        boto_session = boto3.Session(botocore_session=botocore_session)
        
        # Crear recurso
        
        
        return boto_session.resource('dynamodb', region_name=self.region)
    
    def _refresh_credentials(self):
        """Método para refrescar credenciales (usado por AssumeRole)"""
        self._refresh_count += 1
        
        logger.info(f"🔄 Refresh #{self._refresh_count}: Asumiendo rol {self.role_arn}")
        
        try:
            sts_client = boto3.client(
                'sts',
                aws_access_key_id=self.access_key_id,
                aws_secret_access_key=self.secret_access_key,
                region_name=self.region
            )
            
            response = sts_client.assume_role(
                RoleArn=self.role_arn,
                RoleSessionName=f"{self.app_env}-session-{self._refresh_count}",
                DurationSeconds=3600
            )
            
            credentials = response['Credentials']
            
            logger.info(f"✅ Credenciales renovadas (expiran: {credentials['Expiration']})")
            
            return {
                'access_key': credentials['AccessKeyId'],
                'secret_key': credentials['SecretAccessKey'],
                'token': credentials['SessionToken'],
                'expiry_time': credentials['Expiration'].isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error renovando credenciales: {e}")
            raise
    
    def _test_connection(self):
        """Prueba la conexión con DynamoDB"""
        try:
            response = self.table.meta.client.describe_table(TableName=self.table_name)
            logger.info(f"✅ Conexión exitosa!")
            logger.info(f"   Tabla: {self.table_name}")
            logger.info(f"   Estado: {response}")
            logger.info("=" * 60 + "\n")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            if error_code == 'ResourceNotFoundException':
                logger.warning(f"⚠️  Tabla {self.table_name} no existe")
            else:
                logger.error(f"❌ Error en conexión: {e}")
                raise
    
    def get_table(self):
        """Retorna la tabla DynamoDB"""
        return self.table
    
    def get_refresh_count(self) -> int:
        """Retorna el número de veces que se han refrescado las credenciales"""
        return self._refresh_count