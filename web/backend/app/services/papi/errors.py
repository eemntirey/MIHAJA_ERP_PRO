
class PapiError(Exception):
    """Base exception for Papi integration errors."""
    pass


class PapiAuthError(PapiError):
    """Raised when Papi authentication fails (invalid API key)."""
    pass


class PapiValidationError(PapiError):
    """Raised when Papi returns a validation error."""
    pass


class PapiUnavailableError(PapiError):
    """Raised when Papi API is unreachable."""
    pass


class PapiWebhookError(PapiError):
    """Raised when webhook verification fails."""
    pass


class PapiDuplicateWebhookError(PapiError):
    """Raised when a webhook event has already been processed."""
    pass


class PapiInvalidStatusError(PapiError):
    """Raised when webhook payment status is invalid or unexpected."""
    pass
