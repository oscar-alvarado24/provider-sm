class SaveProviderException(Exception):
    """
    Exception raised when there is an error saving a provider.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"SaveProviderException: {self.message}"