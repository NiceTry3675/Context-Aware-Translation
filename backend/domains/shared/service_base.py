"""
Base Service Module

Provides base classes and common functionality for domain services.
Refactored from backend/services/base/base_service.py
"""

import os
import json
import traceback
from typing import Dict, Any, Union, Optional
from pathlib import Path

from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from backend.domains.shared.model_factory import ModelAPIFactory


class ServiceBase:
    """Base class for domain services providing common functionality."""
    
    def __init__(self):
        """Initialize base service."""
        self.config = load_config()
    
    def create_model_api(
        self, 
        api_key: str, 
        model_name: str
    ) -> Union[GeminiModel, OpenRouterModel]:
        """
        Create a model API instance using the factory.
        
        Args:
            api_key: API key for the model service
            model_name: Name of the model to use
            
        Returns:
            Model API instance
        """
        return ModelAPIFactory.create(api_key, model_name, self.config)
    
    def validate_api_key(self, api_key: str, model_name: str) -> bool:
        """
        Validate API key using the factory.
        
        Args:
            api_key: API key to validate
            model_name: Model name to validate against
            
        Returns:
            True if valid, False otherwise
        """
        return ModelAPIFactory.validate_api_key(api_key, model_name)
    
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
    
    def __init__(self, repository=None, uow=None, storage=None):
        """
        Initialize domain service with dependencies.
        
        Args:
            repository: Repository instance for data access
            uow: Unit of Work for transaction management
            storage: Storage abstraction for file operations
        """
        super().__init__()
        self._repository = repository
        self._uow = uow
        self._storage = storage
    
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
    
    def validate_dependencies(self) -> None:
        """
        Validate that required dependencies are configured.
        
        Raises:
            ValueError: If required dependencies are missing
        """
        missing = []
        
        if self._repository is None:
            missing.append("repository")
        if self._uow is None:
            missing.append("unit of work")
        if self._storage is None:
            missing.append("storage")
        
        if missing:
            raise ValueError(
                f"Missing required dependencies: {', '.join(missing)}. "
                f"Configure using with_* methods."
            )