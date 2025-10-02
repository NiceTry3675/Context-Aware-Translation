from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_


T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository defining the interface for data access."""
    
    @abstractmethod
    def get(self, id: Any) -> Optional[T]:
        """Get an entity by its ID."""
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        pass
    
    @abstractmethod
    def add(self, entity: T) -> T:
        """Add a new entity."""
        pass
    
    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass
    
    @abstractmethod
    def delete(self, id: Any) -> bool:
        """Delete an entity by its ID."""
        pass
    
    @abstractmethod
    def exists(self, id: Any) -> bool:
        """Check if an entity exists by its ID."""
        pass


class SqlAlchemyRepository(BaseRepository[T]):
    """SQLAlchemy implementation of the base repository."""
    
    def __init__(self, session: Session, model_class: type):
        """
        Initialize the repository with a session and model class.
        
        Args:
            session: SQLAlchemy session
            model_class: SQLAlchemy model class to operate on
        """
        self.session = session
        self.model_class = model_class
    
    def get(self, id: Any) -> Optional[T]:
        """Get an entity by its ID."""
        return self.session.query(self.model_class).filter(
            self.model_class.id == id
        ).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Get all entities with pagination."""
        return self.session.query(self.model_class).offset(skip).limit(limit).all()
    
    def add(self, entity: T) -> T:
        """Add a new entity."""
        self.session.add(entity)
        self.session.flush()  # Flush to get the ID without committing
        return entity
    
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        self.session.merge(entity)
        self.session.flush()
        return entity
    
    def delete(self, id: Any) -> bool:
        """Delete an entity by its ID."""
        entity = self.get(id)
        if entity:
            self.session.delete(entity)
            self.session.flush()
            return True
        return False
    
    def exists(self, id: Any) -> bool:
        """Check if an entity exists by its ID."""
        return self.session.query(
            self.session.query(self.model_class).filter(
                self.model_class.id == id
            ).exists()
        ).scalar()
    
    def find_by(self, **kwargs) -> List[T]:
        """Find entities by arbitrary keyword arguments."""
        query = self.session.query(self.model_class)
        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        return query.all()
    
    def find_one_by(self, **kwargs) -> Optional[T]:
        """Find a single entity by arbitrary keyword arguments."""
        query = self.session.query(self.model_class)
        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        return query.first()
    
    def count(self, **kwargs) -> int:
        """Count entities matching the given criteria."""
        query = self.session.query(self.model_class)
        for key, value in kwargs.items():
            if hasattr(self.model_class, key):
                query = query.filter(getattr(self.model_class, key) == value)
        return query.count()
    
    def execute_query(self, query):
        """Execute a custom query."""
        return self.session.execute(query)
    
    def bulk_insert(self, entities: List[T]) -> List[T]:
        """Bulk insert multiple entities."""
        self.session.bulk_insert_mappings(
            self.model_class,
            [entity.__dict__ for entity in entities]
        )
        self.session.flush()
        return entities
    
    def filter_by_conditions(self, conditions: List[Any], skip: int = 0, limit: int = 100) -> List[T]:
        """Filter entities by multiple conditions."""
        query = self.session.query(self.model_class)
        if conditions:
            query = query.filter(and_(*conditions))
        return query.offset(skip).limit(limit).all()