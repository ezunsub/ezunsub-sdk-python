"""EZUnsub SDK exceptions."""


class EZUnsubError(Exception):
    """Base exception for EZUnsub SDK."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class AuthenticationError(EZUnsubError):
    """Raised when authentication fails (401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, status_code=401)


class ValidationError(EZUnsubError):
    """Raised when request validation fails (400)."""

    def __init__(self, message: str = "Invalid request"):
        super().__init__(message, status_code=400)


class NotFoundError(EZUnsubError):
    """Raised when a resource is not found (404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class RateLimitError(EZUnsubError):
    """Raised when rate limit is exceeded (429)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class ForbiddenError(EZUnsubError):
    """Raised when access is denied (403)."""

    def __init__(self, message: str = "Access denied"):
        super().__init__(message, status_code=403)
