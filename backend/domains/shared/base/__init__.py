"""
Shared Base Module

Provides base classes and factory patterns for domain services:
- ServiceBase: Basic service functionality
- DomainServiceBase: Domain service with repository and UoW
- ModelAPIFactory: Factory for creating AI model instances
"""

from .service_base import ServiceBase, DomainServiceBase
from .model_factory import ModelAPIFactory

__all__ = [
    'ServiceBase',
    'DomainServiceBase',
    'ModelAPIFactory'
]