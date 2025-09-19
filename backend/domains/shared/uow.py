from typing import Protocol, Any
from sqlalchemy.orm import Session
from contextlib import contextmanager


class UnitOfWork(Protocol):
    """Unit of Work protocol defining the interface for transactional operations."""
    session: Session
    
    def commit(self) -> None:
        """Commit the current transaction."""
        ...
    
    def rollback(self) -> None:
        """Rollback the current transaction."""
        ...
    
    def flush(self) -> None:
        """Flush pending changes to the database without committing."""
        ...


class SqlAlchemyUoW:
    """SQLAlchemy implementation of the Unit of Work pattern."""
    
    def __init__(self, session_factory):
        """
        Initialize the Unit of Work with a session factory.
        
        Args:
            session_factory: A callable that returns a new SQLAlchemy session
        """
        self._session_factory = session_factory
        self.session: Session = None
        self._events: list = []
    
    def __enter__(self):
        """Enter the context manager and create a new session."""
        self.session = self._session_factory()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager, committing or rolling back as needed."""
        try:
            if exc_type:
                self.rollback()
            else:
                try:
                    self.commit()
                except Exception:
                    self.rollback()
                    raise
        finally:
            if self.session:
                self.session.close()
    
    def commit(self):
        """Commit the current transaction and dispatch any collected events."""
        self.session.commit()
        # Events will be dispatched after successful commit
        self._dispatch_events()
    
    def rollback(self):
        """Rollback the current transaction and clear any collected events."""
        if self.session:
            self.session.rollback()
        self._events.clear()
    
    def flush(self):
        """Flush pending changes to the database without committing."""
        self.session.flush()
    
    def collect_event(self, event: Any):
        """Collect a domain event to be dispatched after commit."""
        self._events.append(event)

    def add_event(self, event: Any):
        """Alias for collect_event for backward compatibility."""
        self.collect_event(event)
    
    def _dispatch_events(self):
        """Dispatch collected events after successful commit."""
        # For now, just clear events. Event dispatcher will be implemented later
        events = self._events.copy()
        self._events.clear()
        # TODO: Implement event dispatching
        return events


@contextmanager
def create_uow(session_factory):
    """
    Create a Unit of Work context manager.
    
    Args:
        session_factory: A callable that returns a new SQLAlchemy session
        
    Yields:
        SqlAlchemyUoW: The unit of work instance
    """
    uow = SqlAlchemyUoW(session_factory)
    try:
        with uow:
            yield uow
    except Exception:
        raise