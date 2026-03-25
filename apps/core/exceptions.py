class DomainError(Exception):
    pass


class ValidationError(DomainError):
    pass


class BedrockInvocationError(DomainError):
    pass
