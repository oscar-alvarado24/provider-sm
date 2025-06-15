class BatchWriteException(Exception):
    """Custom exception for errors when performing a batch write operation in DynamoDB."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
    def __str__(self):
        return f"BatchWriteException: {self.message}"