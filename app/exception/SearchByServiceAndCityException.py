class SearchByServiceAndCityException(Exception):
    """
    Exception raised when there is an error searching providers by service and city.
    """
    def __init__(self, message: str ):
        super().__init__(message)
        self.message = message
    def __str__(self):
        return f"SearchByServiceAndCityException: {self.message}"