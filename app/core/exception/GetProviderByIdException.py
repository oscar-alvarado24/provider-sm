class GetProviderByIdException(Exception):
    """Custom exception for errors when cant obtain provider by id."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return f"GetProviderByIdException: {self.message}"