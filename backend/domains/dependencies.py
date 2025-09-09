"""
Dependency injection setup for the domain-driven architecture.

This module provides FastAPI dependencies for accessing repositories,
services, and the Unit of Work in API endpoints.
"""

from typing import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.config.database import SessionLocal
from backend.domains.shared import SqlAlchemyUoW
from backend.domains.translation import (
    SqlAlchemyTranslationJobRepository,
    TranslationUsageLogRepository
)
from backend.domains.user import SqlAlchemyUserRepository
from backend.domains.community import (
    SqlAlchemyPostRepository,
    SqlAlchemyCommentRepository,
    PostCategoryRepository,
    SqlAlchemyAnnouncementRepository
)
from backend.domains.shared import OutboxRepository
from backend.domains.translation.service import TranslationDomainService


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get a database session.
    
    Yields:
        SQLAlchemy session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_uow() -> Generator[SqlAlchemyUoW, None, None]:
    """
    Dependency to get a Unit of Work instance.
    
    Yields:
        Unit of Work for managing transactions
    """
    with SqlAlchemyUoW(SessionLocal) as uow:
        yield uow


# Repository dependencies

def get_translation_job_repository(
    db: Session = Depends(get_db)
) -> SqlAlchemyTranslationJobRepository:
    """Get translation job repository."""
    return SqlAlchemyTranslationJobRepository(db)


def get_translation_usage_repository(
    db: Session = Depends(get_db)
) -> TranslationUsageLogRepository:
    """Get translation usage log repository."""
    return TranslationUsageLogRepository(db)


def get_user_repository(
    db: Session = Depends(get_db)
) -> SqlAlchemyUserRepository:
    """Get user repository."""
    return SqlAlchemyUserRepository(db)


def get_post_repository(
    db: Session = Depends(get_db)
) -> SqlAlchemyPostRepository:
    """Get post repository."""
    return SqlAlchemyPostRepository(db)


def get_comment_repository(
    db: Session = Depends(get_db)
) -> SqlAlchemyCommentRepository:
    """Get comment repository."""
    return SqlAlchemyCommentRepository(db)


def get_category_repository(
    db: Session = Depends(get_db)
) -> PostCategoryRepository:
    """Get post category repository."""
    return PostCategoryRepository(db)


def get_announcement_repository(
    db: Session = Depends(get_db)
) -> SqlAlchemyAnnouncementRepository:
    """Get announcement repository."""
    return SqlAlchemyAnnouncementRepository(db)


def get_outbox_repository(
    db: Session = Depends(get_db)
) -> OutboxRepository:
    """Get outbox repository for domain events."""
    return OutboxRepository(db)


# Service dependencies

def get_translation_service() -> TranslationDomainService:
    """
    Get translation domain service.
    
    Returns:
        TranslationDomainService instance
    """
    return TranslationDomainService(SessionLocal)


# Composite dependencies for complex operations

class RepositoryBundle:
    """Bundle of commonly used repositories."""
    
    def __init__(
        self,
        translation_job_repo: SqlAlchemyTranslationJobRepository,
        user_repo: SqlAlchemyUserRepository,
        outbox_repo: OutboxRepository
    ):
        self.translation_job = translation_job_repo
        self.user = user_repo
        self.outbox = outbox_repo


def get_repository_bundle(
    db: Session = Depends(get_db)
) -> RepositoryBundle:
    """
    Get a bundle of commonly used repositories.
    
    This is useful when an endpoint needs multiple repositories.
    """
    return RepositoryBundle(
        translation_job_repo=SqlAlchemyTranslationJobRepository(db),
        user_repo=SqlAlchemyUserRepository(db),
        outbox_repo=OutboxRepository(db)
    )


# Configuration for dependency overrides in testing

def get_test_db() -> Generator[Session, None, None]:
    """
    Test database session dependency.
    
    This can be used to override the production database in tests.
    """
    # In tests, this would use a test database
    from tests.fixtures import TestDatabase
    test_db = TestDatabase()
    try:
        yield test_db.session
    finally:
        test_db.cleanup()


def override_dependencies_for_testing(app):
    """
    Override dependencies for testing.
    
    Args:
        app: FastAPI application instance
    """
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_translation_service] = lambda: TranslationDomainService(
        lambda: get_test_db().__next__()
    )