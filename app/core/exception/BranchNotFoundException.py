class BranchNotFoundException(Exception):
    """
    Exception raised when a branch is not found.
    """
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"BranchNotFoundException: {self.message}"