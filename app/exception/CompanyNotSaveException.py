class CompanyNotSaveException(Exception):
    """
    Exception raised when a company cannot be saved.
    """

    def __init__(self, message: str ):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"CompanyNotSaveException: {self.message}"