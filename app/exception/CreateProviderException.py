class CreateProviderException(Exception):
    """Custom excepción for errors when creating a provider."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"CreateProviderException: {self.message}"