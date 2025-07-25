class ServiceError(Exception):
    """Raised by service functions on business errors."""

    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
