class GetBranchByIdException(Exception):
    """
    Exception raised when there is an error getting a branch by its ID.
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"GetBranchByIdException: {self.message}"