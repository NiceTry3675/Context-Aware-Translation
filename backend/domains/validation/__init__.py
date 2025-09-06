"""Validation domain package."""

from .service import ValidationDomainService

# Import ValidationRoutes lazily to avoid circular imports
def get_validation_routes():
    from .routes import ValidationRoutes
    return ValidationRoutes

__all__ = ["ValidationDomainService", "get_validation_routes"]