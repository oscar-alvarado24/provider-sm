import os
from typing import Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError
from app.core.config import settings as app_settings

class DynamoConnection:
    def __init__(self):

        self.table_name = app_settings.dynamodb_table_name
        print("Nombre de tabla al inicializar:", self.table_name)
        self.region_name = app_settings.aws_region_name
        self.endpoint_url = app_settings.dynamodb_endpoint_url

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
               
    def _configure_credentials(self, dynamodb_args: Dict[str, Any]):
        """Configura las credenciales de AWS de forma robusta"""
        # Si es endpoint local (DynamoDB Local), usar credenciales dummy
        if self.endpoint_url and ('localhost' in self.endpoint_url or '127.0.0.1' in self.endpoint_url):
            print("Detected local DynamoDB endpoint, using dummy credentials")
            dynamodb_args['aws_access_key_id'] = 'dummy'
            dynamodb_args['aws_secret_access_key'] = 'dummy'
            return
        
        # Para endpoints reales, verificar credenciales
        access_key = app_settings.aws_access_key_id
        secret_key = app_settings.aws_secret_access_key
        session_token = app_settings.aws_session_token

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
