from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import re

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
    secret_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

    def get_origin_regex(self) -> str:
        """Convierte los patrones de origin en una expresión regular"""
        if not self.origin:
            return r"^http://localhost:4200$"

        if self.origin == "*":
            return r".*"

        # Dividir los orígenes por coma
        origins = [origin.strip() for origin in self.origin.split(",")]

        # Convertir cada patrón a regex
        regex_patterns = []
        for origin in origins:
            # Escapar caracteres especiales excepto *
            pattern = re.escape(origin)
            # Reemplazar \* (escapado) con .* (regex para cualquier carácter)
            pattern = pattern.replace(r"\*", ".*")
            regex_patterns.append(f"({pattern})")

        # Combinar todos los patrones con OR (|)
        combined_pattern = "|".join(regex_patterns)

        return f"^({combined_pattern})$"

settings = Settings()
