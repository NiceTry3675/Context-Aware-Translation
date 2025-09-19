import os
import sys
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure required settings variables exist for Settings() used in services
os.environ.setdefault("GEMINI_API_KEY", "test-gemini")
os.environ.setdefault("CLERK_SECRET_KEY", "test-clerk")
os.environ.setdefault("ADMIN_SECRET_KEY", "test-admin")

from backend.domains.shared.db_base import Base
from backend.domains.translation.models import TranslationJob, TranslationUsageLog
from backend.domains.user.models import User
from backend.domains.user.service import UserService
from core.translation.progress_tracker import ProgressTracker
from core.translation.usage_tracker import TokenUsageCollector, UsageEvent


@pytest.fixture()
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


def create_user(db: Session, index: int = 1) -> User:
    user = User(
        clerk_user_id=f"user_{index}",
        email=f"user{index}@example.com",
        name=f"User {index}",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_job(db: Session, owner: User | None = None, filename: str = "sample.txt") -> TranslationJob:
    job = TranslationJob(filename=filename, owner_id=owner.id if owner else None)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def test_usage_event_normalization() -> None:
    event = UsageEvent(model_name="model", prompt_tokens=-5, completion_tokens=3, total_tokens=None)
    normalized = event.normalized()

    assert normalized.prompt_tokens == 0
    assert normalized.completion_tokens == 3
    assert normalized.total_tokens == 0


def test_token_usage_collector_records_events() -> None:
    collector = TokenUsageCollector()
    collector.record_event(UsageEvent(model_name="model-a", prompt_tokens=10, completion_tokens=5, total_tokens=15))
    collector.record_event("invalid")  # type: ignore[arg-type]
    collector.record_event(UsageEvent(model_name="model-b"))  # zero-token event should still be recorded

    events = collector.events()
    assert len(events) == 2
    assert events[0].prompt_tokens == 10
    assert events[0].total_tokens == 15
    assert events[1].total_tokens == 0

    collector.clear()
    assert collector.events() == []


def test_progress_tracker_records_usage_logs(session: Session) -> None:
    user = create_user(session)
    job = create_job(session, owner=user)

    tracker = ProgressTracker(db=session, job_id=job.id)
    tracker.record_usage_log(
        original_text="hello",
        translated_text="world",
        model_name="gemini-pro",
        token_events=[
            UsageEvent(model_name="gemini-pro", prompt_tokens=42, completion_tokens=11, total_tokens=53),
            UsageEvent(model_name="openrouter/claude", prompt_tokens=0, completion_tokens=5, total_tokens=None),
        ],
    )

    logs = session.query(TranslationUsageLog).order_by(TranslationUsageLog.id).all()
    assert len(logs) == 2
    assert all(log.user_id == user.id for log in logs)
    assert logs[0].model_used == "gemini-pro"
    assert logs[0].prompt_tokens == 42
    assert logs[0].completion_tokens == 11
    assert logs[0].total_tokens == 53
    assert logs[1].model_used == "openrouter/claude"
    assert logs[1].prompt_tokens == 0
    assert logs[1].completion_tokens == 5
    assert logs[1].total_tokens == 5  # total inferred when missing


def test_progress_tracker_skips_logs_without_owner(session: Session) -> None:
    job = create_job(session, owner=None)

    tracker = ProgressTracker(db=session, job_id=job.id)
    tracker.record_usage_log(
        original_text="hello",
        translated_text="world",
        model_name="gemini-pro",
        token_events=[UsageEvent(model_name="gemini-pro", prompt_tokens=10, completion_tokens=5, total_tokens=15)],
    )

    logs = session.query(TranslationUsageLog).all()
    assert logs == []


def test_progress_tracker_creates_default_event_when_missing(session: Session) -> None:
    user = create_user(session, index=2)
    job = create_job(session, owner=user, filename="second.txt")

    tracker = ProgressTracker(db=session, job_id=job.id)
    tracker.record_usage_log(
        original_text="text",
        translated_text="translated",
        model_name="gemini-flash",
        token_events=None,
    )

    logs = session.query(TranslationUsageLog).all()
    assert len(logs) == 1
    log = logs[0]
    assert log.model_used == "gemini-flash"
    assert log.total_tokens == 0
    assert log.user_id == user.id


def test_user_service_token_usage_dashboard(session: Session) -> None:
    user = create_user(session, index=3)
    job = create_job(session, owner=user, filename="dashboard.txt")

    now = datetime.utcnow()
    older = now - timedelta(days=1)

    session.add_all([
        TranslationUsageLog(
            job_id=job.id,
            user_id=user.id,
            original_length=100,
            translated_length=120,
            translation_duration_seconds=30,
            model_used="gemini-pro",
            prompt_tokens=60,
            completion_tokens=40,
            total_tokens=100,
            created_at=older,
        ),
        TranslationUsageLog(
            job_id=job.id,
            user_id=user.id,
            original_length=80,
            translated_length=90,
            translation_duration_seconds=25,
            model_used="openrouter/claude",
            prompt_tokens=30,
            completion_tokens=20,
            total_tokens=50,
            created_at=now,
        ),
    ])
    session.commit()

    service = UserService(session)
    summary = service.get_token_usage_dashboard(user.id)

    assert summary['total']['input_tokens'] == 90
    assert summary['total']['output_tokens'] == 60
    assert summary['total']['total_tokens'] == 150
    assert summary['last_updated'] == max(log.created_at for log in session.query(TranslationUsageLog).all())

    per_model = {entry['model']: entry for entry in summary['per_model']}
    assert per_model['gemini-pro']['total_tokens'] == 100
    assert per_model['openrouter/claude']['input_tokens'] == 30
