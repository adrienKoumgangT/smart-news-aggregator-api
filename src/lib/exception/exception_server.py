class UnsafeException(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code


class SafeException(Exception):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundException(SafeException):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is None:
            return f"NotFoundException: {self.message}"
        else:
            return f"NotFoundException: {self.code} - {self.message}"


class UnauthorizedException(SafeException):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is None:
            return f"UnauthorizedException: {self.message}"
        else:
            return f"UnauthorizedException: {self.code} - {self.message}"


class InvalidClassException(SafeException):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is None:
            return f"InvalidClassException: {self.message}"
        else:
            return f"InvalidClassException: {self.code} - {self.message}"


class InvalidKeyException(SafeException):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is None:
            return f"InvalidKeyException: {self.message}"
        else:
            return f"InvalidKeyException: {self.code} - {self.message}"


class InvalidValueException(SafeException):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is None:
            return f"InvalidValueException: {self.message}"
        else:
            return f"InvalidValueException: {self.code} - {self.message}"


class TokenException(SafeException):
    def __init__(self, message, code=None):
        super().__init__(message)
        self.message = message
        self.code = code

    def __str__(self):
        if self.code is None:
            return f"TokenException: {self.message}"
        else:
            return f"TokenException: {self.code} - {self.message}"
