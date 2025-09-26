class CompanyNotDeletedException(Exception):
    """
    Exception raised when a company cannot be deleted.
    """

    def __init__(self, message: str ):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"CompanyNotDeletedException: {self.message}"