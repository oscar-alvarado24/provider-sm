class CompanyNotUpdateException(Exception):
    """
    Exception raised when a company cannot be updated.
    """

    def __init__(self, message: str ):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"CompanyNotUpdateException: {self.message}"