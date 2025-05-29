from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    app_name: str = "Provider Microservice"
    app_version: str = "0.1.0"
    aws_region_name: Optional[str] = None
    dynamodb_table_name: str = "providers"
    dynamodb_endpoint_url: Optional[str] = None # For DynamoDB Local

    # If you have a .env file, its values will override defaults
    # For pydantic-settings v2.x.x
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')
    # For pydantic-settings v1.x.x (older versions)
    # class Config:
    #     env_file = ".env"
    #     env_file_encoding = 'utf-8'
    #     extra = 'ignore'


settings = Settings()
