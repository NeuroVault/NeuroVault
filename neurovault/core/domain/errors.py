class DomainError(Exception):
    """A rule of the domain was broken."""


class DomainValidationError(DomainError):
    """Invalid input, reported per field: {field name: [messages]}."""

    def __init__(self, errors):
        if isinstance(errors, str):
            errors = {"__all__": [errors]}
        self.errors = errors
        super().__init__(errors)


class NotFound(DomainError):
    pass


class PermissionDenied(DomainError):
    pass
