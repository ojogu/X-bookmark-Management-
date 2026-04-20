# Custom Exception Classes


class BaseExceptionClass(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class Environment_Variable_Exception(BaseExceptionClass):
    pass


class InUseError(BaseExceptionClass):
    pass


class InvalidToken(BaseExceptionClass):
    pass


class TokenExpired(BaseExceptionClass):
    pass


class NotFoundError(BaseExceptionClass):
    pass


class AlreadyExistsError(BaseExceptionClass):
    pass


class InvalidEmailPassword(BaseExceptionClass):
    pass

class Unauthorized(BaseExceptionClass):
    pass


class BadRequest(BaseExceptionClass):
    pass


class NotVerified(BaseExceptionClass):
    pass


class EmailVerificationError(BaseExceptionClass):
    pass


class DatabaseError(BaseExceptionClass):
    pass


class ServerError(BaseExceptionClass):
    pass


class NotActive(BaseExceptionClass):
    pass


class ExternalAPIError(Exception):
    """Raised when external API returns an error status"""

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)

    @property
    def is_rate_limited(self) -> bool:
        return self.status_code == 429

    @property
    def is_server_error(self) -> bool:
        return self.status_code and 500 <= self.status_code < 600
