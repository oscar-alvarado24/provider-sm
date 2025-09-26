class GetCompanyException(Exception):
    """
    Exception raised when a error succes to the consult in db .
    """
    def __init__(self, message: str ):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"GetCompanyException: {self.message}"