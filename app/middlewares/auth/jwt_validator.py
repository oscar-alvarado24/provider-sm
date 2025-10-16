import requests
from jose import jwt, JWTError
from typing import Dict
from fastapi import HTTPException, status
from functools import lru_cache

class CognitoJWTValidator:
    def __init__(self, region: str, user_pool_id: str, app_client_id: str):
        self.region = region
        self.user_pool_id = user_pool_id
        self.app_client_id = app_client_id
        self.jwks_url = f"https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json"
        self._jwks = None
    
    @lru_cache(maxsize=1)
    def get_jwks(self) -> Dict:
        """Obtiene las claves públicas de Cognito (con cache)"""
        if not self._jwks:
            response = requests.get(self.jwks_url)
            self._jwks = response.json()
        return self._jwks
    
    def get_signing_key(self, token: str) -> str:
        """Obtiene la clave pública correspondiente al token"""
        try:
            # Decodifica el header sin verificar
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header['kid']
            
            # Busca la clave correspondiente
            jwks = self.get_jwks()
            for key in jwks['keys']:
                if key['kid'] == kid:
                    return key
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Clave de firma no encontrada"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error al obtener clave de firma: {str(e)}"
            )
    
    def verify_token(self, token: str) -> Dict:
        """Verifica y decodifica el token JWT de Cognito"""
        try:
            # Obtiene la clave pública
            signing_key = self.get_signing_key(token)
            
            # Verifica y decodifica el token
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=['RS256'],
                audience=self.app_client_id,
                issuer=f"https://cognito-idp.{self.region}.amazonaws.com/{self.user_pool_id}"
            )
            
            return payload
            
        except JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Token inválido: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error al verificar token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"}
            )