"""
Module with the class CryptoService that contain the code for encrypt and decrypt
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class CryptoService:
    """
    Class with the service in charge of managing the encryption and deencryption process
    """
    def __init__(self, secret_key: str):
        """
        Inicializa el servicio con la clave secreta en base64

        Args:
            secret_key: Clave en base64 (debe ser 32 bytes cuando se decodifica)
        """
        self.secret_key = secret_key.strip().replace('\n', '').replace('\r', '') if secret_key else ''
        self.is_key_validated = False
        self._validate_key(secret_key)

    def _validate_key(self, secret_key: str) -> None:
        """Valida que la clave sea base64 válido y tenga 32 bytes (256 bits)"""
        try:
            if not self.is_key_validated:
                key_bytes = base64.b64decode(secret_key)
                if len(key_bytes) != 32:
                    raise ValueError(f'''La clave debe ser base64 de
                                     32 bytes (256 bits), pero tiene
                                     {len(key_bytes)} bytes''')
                self.is_key_validated = True
        except Exception as e:
            raise ValueError(f'La clave debe ser un base64 válido: {str(e)}') from e

    def encrypt(self, data: str) -> str:
        """
        Encripta los datos usando AES-256-GCM

        Args:
            data: String a encriptar

        Returns:
            String con formato base64 (IV + datos encriptados)
        """
        key_bytes = base64.b64decode(self.secret_key)

        iv = os.urandom(12)

        data_bytes = data.encode('utf-8')

        cipher = AESGCM(key_bytes)
        encrypted_data = cipher.encrypt(iv, data_bytes, None)

        combined = iv + encrypted_data

        return self._to_url_safe_base64(combined)

    def decrypt(self, encrypted_data: str) -> str:
        """
        Desencripta los datos usando AES-256-GCM

        Args:
            encrypted_data: String en base64 (IV + datos encriptados)

        Returns:
            String desencriptado
        """
        try:
            key_bytes = base64.b64decode(self.secret_key)

            encrypted_buffer = self._from_url_safe_base64(encrypted_data)

            iv = encrypted_buffer[:12]
            data = encrypted_buffer[12:]

            cipher = AESGCM(key_bytes)
            decrypted_data = cipher.decrypt(iv, data, None)

            return decrypted_data.decode('utf-8')
        except Exception as e:
            raise ValueError(f'''Error al desencriptar: clave
                             incorrecta o datos corruptos - {str(e)}''') from e

    def _to_url_safe_base64(self, data: bytes) -> str:
        """Convierte bytes a base64 URL-safe sin padding"""
        return base64.b64encode(data).decode('utf-8').replace('+', '-').replace('/', '_').rstrip('=')

    def _from_url_safe_base64(self, data: str) -> bytes:
        """Convierte base64 URL-safe a bytes"""
        # Restaurar caracteres estándar
        standard_base64 = data.replace('-', '+').replace('_', '/')

        # Restaurar padding
        padding = (4 - len(standard_base64) % 4) % 4
        standard_base64 += '=' * padding

        return base64.b64decode(standard_base64)
