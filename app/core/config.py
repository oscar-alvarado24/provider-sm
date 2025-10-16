from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Provider Microservice"
    app_version: str = "0.1.0"
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""
    aws_region: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None
    aws_dynamo_role: Optional[str] = None
    dynamodb_table_name: Optional[str] = None
    dynamodb_endpoint_url: Optional[str] = None 
    origin: Optional[str] = None
    environment: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')
    


settings = Settings()
