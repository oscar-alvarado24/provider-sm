class ProviderNotFoundException(Exception):
    """
    Exception raised when a provider is not found.
    """
    def __init__(self, message: str ):
        super().__init__(message)
        self.message = message
    def __str__(self):
        return f"ProviderNotFoundException: {self.message}"