"""
Base Service Module

Provides base classes and common functionality for domain services.
Refactored from backend/services/base/base_service.py
"""

import os
import json
import traceback
import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union
from pathlib import Path
from contextlib import contextmanager
from functools import wraps

from fastapi import HTTPException
from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from core.translation.usage_tracker import UsageEvent
from backend.domains.shared.model_factory import ModelAPIFactory
from backend.domains.shared.provider_context import ProviderContext, parse_provider_context
from backend.domains.shared.utils.file_manager import FileManager

# Type variable for repository classes
T = TypeVar('T')


class ServiceBase:
    """Base class for domain services providing common functionality."""
    
    def __init__(self):
        """Initialize base service."""
        self.config = load_config()
        self._file_manager = None
        self._logger = None
    
    @property
    def file_manager(self) -> FileManager:
        """
        Lazy-loaded file manager property.
        
        Returns:
            FileManager instance
        """
        if self._file_manager is None:
            self._file_manager = FileManager()
        return self._file_manager
    
    @property
    def logger(self) -> logging.Logger:
        """
        Lazy-loaded logger property.
        
        Returns:
            Logger instance for this service
        """
        if self._logger is None:
            self._logger = logging.getLogger(self.__class__.__name__)
        return self._logger
    
    def create_model_api(
        self,
        api_key: Optional[str],
        model_name: str,
        provider_context: Optional[ProviderContext] = None,
        usage_callback: Callable[[UsageEvent], None] | None = None,
        *,
        backup_api_keys: list[str] | None = None,
        requests_per_minute: int | None = None,
    ) -> Union[GeminiModel, OpenRouterModel]:
        """
        Create a model API instance using the factory.
        
        Args:
            api_key: API key for the model service
            model_name: Name of the model to use
            
        Returns:
            Model API instance
        """
        return ModelAPIFactory.create(
            api_key=api_key,
            model_name=model_name,
            config=self.config,
            provider_context=provider_context,
            usage_callback=usage_callback,
            backup_api_keys=backup_api_keys,
            requests_per_minute=requests_per_minute,
        )

    def validate_api_key(
        self,
        api_key: Optional[str],
        model_name: str,
        provider_context: Optional[ProviderContext] = None,
        *,
        backup_api_keys: list[str] | None = None,
    ) -> bool:
        """
        Validate API key using the factory.
        
        Args:
            api_key: API key to validate
            model_name: Model name to validate against
            
        Returns:
            True if valid, False otherwise
        """
        return ModelAPIFactory.validate_api_key(
            api_key=api_key,
            model_name=model_name,
            provider_context=provider_context,
            backup_api_keys=backup_api_keys,
        )

    def validate_and_create_model(
        self,
        api_key: Optional[str],
        model_name: str,
        provider_context: Optional[ProviderContext] = None,
        usage_callback: Callable[[UsageEvent], None] | None = None,
        *,
        backup_api_keys: list[str] | None = None,
        requests_per_minute: int | None = None,
    ) -> Union[GeminiModel, OpenRouterModel]:
        """
        Validate API key and create model in one step.
        
        Args:
            api_key: API key for the model service
            model_name: Name of the model to use
            
        Returns:
            Model API instance
            
        Raises:
            HTTPException: If API key is invalid
        """
        try:
            if not self.validate_api_key(
                api_key,
                model_name,
                provider_context=provider_context,
                backup_api_keys=backup_api_keys,
            ):
                self.raise_invalid_api_key()
        except ValueError as exc:
            self.raise_validation_error(str(exc))
        return self.create_model_api(
            api_key,
            model_name,
            provider_context=provider_context,
            usage_callback=usage_callback,
            backup_api_keys=backup_api_keys,
            requests_per_minute=requests_per_minute,
        )

    def build_provider_context(
        self,
        provider: Optional[str],
        provider_payload: Any,
    ) -> ProviderContext:
        """Parse the incoming provider payload into a ProviderContext."""

        provider_name = provider or "gemini"
        return parse_provider_context(provider_name, provider_payload)
    
    def raise_invalid_api_key(self):
        """Raise standardized invalid API key exception."""
        raise HTTPException(
            status_code=400, 
            detail="Invalid API Key or unsupported model."
        )
    
    def raise_not_found(self, resource: str):
        """
        Raise standardized not found exception.
        
        Args:
            resource: Name of the resource that was not found
        """
        raise HTTPException(
            status_code=404, 
            detail=f"{resource} not found"
        )
    
    def raise_validation_error(self, message: str):
        """
        Raise standardized validation error exception.
        
        Args:
            message: Validation error message
        """
        raise HTTPException(
            status_code=422,
            detail=message
        )
    
    def raise_forbidden(self, message: str = "Access forbidden"):
        """
        Raise standardized forbidden exception.
        
        Args:
            message: Optional custom message
        """
        raise HTTPException(
            status_code=403,
            detail=message
        )
    
    def raise_conflict(self, message: str):
        """
        Raise standardized conflict exception.
        
        Args:
            message: Conflict description
        """
        raise HTTPException(
            status_code=409,
            detail=message
        )
    
    def raise_server_error(self, message: str = "Internal server error"):
        """
        Raise standardized server error exception.
        
        Args:
            message: Optional custom message
        """
        raise HTTPException(
            status_code=500,
            detail=message
        )
    
    def handle_error(
        self, 
        error: Exception, 
        context: str = ""
    ) -> Dict[str, Any]:
        """
        Handle errors consistently across services.
        
        Args:
            error: Exception that occurred
            context: Additional context information
            
        Returns:
            Error response dictionary
        """
        error_message = str(error)
        
        # Add context if provided
        if context:
            error_message = f"{context}: {error_message}"
        
        # Log the full traceback for debugging
        print(f"Error in {self.__class__.__name__}: {error_message}")
        print(traceback.format_exc())
        
        return {
            "error": error_message,
            "service": self.__class__.__name__,
            "context": context
        }
    
    def save_structured_output(
        self, 
        data: Dict[str, Any], 
        filepath: str
    ) -> None:
        """
        Save structured data to file.
        
        Args:
            data: Data to save
            filepath: File path to save to
        """
        # Ensure directory exists
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_structured_data(self, filepath: str) -> Dict[str, Any]:
        """
        Load structured data from file.
        
        Args:
            filepath: File path to load from
            
        Returns:
            Loaded data dictionary
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not Path(filepath).exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)


class DomainServiceBase(ServiceBase):
    """
    Base class for domain services with repository and UoW support.
    """
    
    def __init__(self, session_factory=None, repository=None, uow=None, storage=None):
        """
        Initialize domain service with dependencies.
        
        Args:
            session_factory: Database session factory for creating sessions
            repository: Repository instance for data access
            uow: Unit of Work for transaction management
            storage: Storage abstraction for file operations
        """
        super().__init__()
        self._session_factory = session_factory
        self._repository = repository
        self._uow = uow
        self._storage = storage
        self._collected_events = []
    
    def with_repository(self, repository):
        """
        Set or update the repository instance.
        
        Args:
            repository: Repository instance
            
        Returns:
            Self for method chaining
        """
        self._repository = repository
        return self
    
    def with_uow(self, uow):
        """
        Set or update the Unit of Work instance.
        
        Args:
            uow: Unit of Work instance
            
        Returns:
            Self for method chaining
        """
        self._uow = uow
        return self
    
    def with_storage(self, storage):
        """
        Set or update the storage instance.
        
        Args:
            storage: Storage instance
            
        Returns:
            Self for method chaining
        """
        self._storage = storage
        return self
    
    def with_session_factory(self, session_factory):
        """
        Set or update the session factory.
        
        Args:
            session_factory: Database session factory
            
        Returns:
            Self for method chaining
        """
        self._session_factory = session_factory
        return self
    
    def get_or_create_repository(self, session, repository_class: Type[T]) -> T:
        """
        Get existing repository or create new one.
        
        Args:
            session: Database session
            repository_class: Repository class to instantiate
            
        Returns:
            Repository instance
        """
        if self._repository:
            return self._repository
        return repository_class(session)
    
    @contextmanager
    def unit_of_work(self):
        """
        Context manager for UoW operations.
        
        Yields:
            Unit of Work instance
            
        Raises:
            ValueError: If no UoW or session_factory configured
        """
        if self._uow:
            yield self._uow
        elif self._session_factory:
            # Import here to avoid circular dependency
            from backend.domains.shared.uow import SqlAlchemyUoW
            with SqlAlchemyUoW(self._session_factory) as uow:
                # Collect events from UoW
                if hasattr(uow, 'events'):
                    self._collected_events.extend(uow.events)
                yield uow
        else:
            raise ValueError("No UoW or session_factory configured")
    
    def transactional(self, func):
        """
        Decorator for transactional operations.
        
        Args:
            func: Function to wrap in a transaction
            
        Returns:
            Wrapped function
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            async with self.unit_of_work() as uow:
                result = await func(*args, **kwargs, uow=uow)
                await uow.commit()
                return result
        return wrapper
    
    def add_event(self, event):
        """
        Add a domain event to be collected.
        
        Args:
            event: Domain event to add
        """
        self._collected_events.append(event)
    
    def get_events(self) -> list:
        """
        Get and clear collected events.
        
        Returns:
            List of collected events
        """
        events = self._collected_events.copy()
        self._collected_events.clear()
        return events
    
    def validate_dependencies(self) -> None:
        """
        Validate that required dependencies are configured.
        
        Raises:
            ValueError: If required dependencies are missing
        """
        missing = []
        
        if self._repository is None:
            missing.append("repository")
        if self._uow is None and self._session_factory is None:
            missing.append("unit of work or session_factory")
        if self._storage is None:
            missing.append("storage")
        
        if missing:
            raise ValueError(
                f"Missing required dependencies: {', '.join(missing)}. "
                f"Configure using with_* methods."
            )
