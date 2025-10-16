class DeleteProviderException(Exception):
    """Custom exception for errors when deleting a provider in DynamoDB."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"DeleteProviderException: {self.message}"