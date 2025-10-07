class EmailVerificationError(Exception):
    """Custom exception for email verification errors."""

    pass


class TemplateRenderingError(Exception):
    """Custom exception for template rendering errors."""

    pass


class EmailDeliveryError(Exception):
    """Custom exception for email delivery errors."""

    pass
