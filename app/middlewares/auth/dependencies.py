from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Optional, List
from .jwt_validator import CognitoJWTValidator
from app.core.config import settings as app_settings

class CustomHTTPBearer(HTTPBearer):
    def __init__(self):
        super().__init__(auto_error=False) 
        
    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials:
        credentials = await super().__call__(request)
        if credentials is None:
            print ("Peticion sin token")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Se requiere token",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return credentials

# Usa la clase personalizada en lugar de HTTPBearer()
security = CustomHTTPBearer()

# Inicializa el validador
jwt_validator = CognitoJWTValidator(
    region=app_settings.aws_region or "us-east-1",
    user_pool_id=app_settings.cognito_user_pool_id,
    app_client_id=app_settings.cognito_app_client_id
)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """
    Dependencia que verifica el token y retorna la información del usuario
    """
    token = credentials.credentials
    payload = jwt_validator.verify_token(token)
    return payload

def require_groups(required_groups: List[str]):
    """
    Dependencia para verificar que el usuario pertenezca a ciertos grupos de Cognito
    """
    def verify_groups(current_user: Dict = Depends(get_current_user)):
        user_groups = current_user.get('cognito:groups', [])
        
        if not any(group in user_groups for group in required_groups):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere pertenecer a uno de estos grupos: {required_groups}"
            )
        return current_user
    
    return verify_groups