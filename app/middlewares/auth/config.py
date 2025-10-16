from pydantic_settings import BaseSettings
from app.core.config import settings as app_settings

class Settings(BaseSettings):
    COGNITO_REGION: str = app_settings.aws_region_name or "us-east-1"
    COGNITO_USER_POOL_ID: str = app_settings.cognito_user_pool_id
    COGNITO_APP_CLIENT_ID: str = app_settings.cognito_app_client_id
  
    @property
    def COGNITO_JWKS_URL(self) -> str:
        return f"https://cognito-idp.{self.COGNITO_REGION}.amazonaws.com/{self.COGNITO_USER_POOL_ID}/.well-known/jwks.json"
    
    class Config:
        env_file = ".env"

settings = Settings()