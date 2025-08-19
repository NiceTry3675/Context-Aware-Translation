"""
Base infrastructure for backend services.

This module provides shared infrastructure components including:
- ModelAPIFactory: Centralized model API creation
- BaseService: Common service patterns and utilities
"""

from .model_factory import ModelAPIFactory
from .base_service import BaseService

__all__ = ['ModelAPIFactory', 'BaseService']