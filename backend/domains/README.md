# Domain-Driven Backend Architecture

## Overview

This directory contains the refactored backend architecture implementing Domain-Driven Design (DDD) patterns with:

- **Repository Pattern**: Abstract data access layer
- **Unit of Work Pattern**: Transaction management
- **Domain Events**: Decoupled communication via outbox pattern
- **Domain Services**: Business logic encapsulation

## Directory Structure

```
domains/
├── shared/              # Shared infrastructure components
│   ├── uow.py          # Unit of Work implementation
│   ├── repository.py   # Base repository classes
│   ├── events.py       # Domain event definitions
│   └── outbox.py       # Outbox pattern for reliable events
├── translation/         # Translation domain
│   ├── repository.py   # Translation job repositories
│   └── service.py      # Translation business logic
├── user/               # User management domain
│   └── repository.py   # User repository with Clerk integration
├── community/          # Community features domain
│   └── repository.py   # Post, Comment, Announcement repositories
└── dependencies.py     # FastAPI dependency injection
```

## Key Components

### 1. Unit of Work (UoW)

Manages database transactions and ensures consistency:

```python
from backend.domains.shared import SqlAlchemyUoW

with SqlAlchemyUoW(session_factory) as uow:
    repo = TranslationJobRepository(uow.session)
    job = repo.add(new_job)
    uow.commit()  # Commits transaction
    # Automatic rollback on exception
```

### 2. Repository Pattern

Abstracts data access with consistent interface:

```python
from backend.domains.translation import SqlAlchemyTranslationJobRepository

# In your service or endpoint
repo = SqlAlchemyTranslationJobRepository(session)
job = repo.get(job_id)
jobs = repo.list_by_user(user_id, limit=10)
```

### 3. Domain Events

Decouple components through event-driven communication:

```python
from backend.domains.shared import TranslationJobCompletedEvent, OutboxRepository

# Publish event (stored in outbox)
event = TranslationJobCompletedEvent(job_id=123, duration_seconds=60)
outbox_repo.add_event(event)

# Events are processed asynchronously by background task
```

### 4. Domain Services

Encapsulate business logic and coordinate repositories:

```python
from backend.domains.translation.service import TranslationDomainService

service = TranslationDomainService(session_factory)
job = service.create_translation_job(
    filename="document.txt",
    owner_id=user_id,
    idempotency_key="unique-key"  # Prevents duplicate jobs
)
```

## Usage Examples

### Creating a Translation Job (with idempotency)

```python
@router.post("/jobs")
async def create_job(
    file: UploadFile,
    service: TranslationDomainService = Depends(get_translation_service)
):
    # Service handles repository, UoW, and events
    job = service.create_translation_job(
        filename=file.filename,
        owner_id=current_user.id,
        idempotency_key=generate_key(file)
    )
    return job
```

### Using Repository with UoW

```python
from backend.domains.shared import SqlAlchemyUoW
from backend.domains.user import SqlAlchemyUserRepository

def update_user_role(user_id: int, new_role: str):
    with SqlAlchemyUoW(SessionLocal) as uow:
        user_repo = SqlAlchemyUserRepository(uow.session)
        
        # All operations in same transaction
        user_repo.update_role(user_id, new_role)
        
        # Create audit event
        event = UserRoleChangedEvent(user_id, old_role, new_role)
        OutboxRepository(uow.session).add_event(event)
        
        # Commit atomically
        uow.commit()
```

### Processing Domain Events

The outbox pattern ensures reliable event delivery:

```python
# Background task (runs periodically)
from backend.background_tasks.event_dispatcher_task import process_outbox_events

async def event_processor():
    # Process events from outbox table
    stats = await process_outbox_events(batch_size=100)
    print(f"Processed {stats['processed']} events")
```

## Migration from Old Architecture

### Old Way (Direct CRUD)
```python
# Before - Direct database access
from backend import crud
job = crud.get_job(db, job_id)
crud.update_job_status(db, job_id, "completed")
```

### New Way (Repository + Service)
```python
# After - Using repository pattern
from backend.domains.translation.service import TranslationDomainService
service = TranslationDomainService(session_factory)
service.complete_translation(job_id, duration_seconds=60)
```

## Benefits

1. **Separation of Concerns**: Business logic separated from data access
2. **Testability**: Easy to mock repositories for unit testing
3. **Consistency**: UoW ensures transactional consistency
4. **Scalability**: Event-driven architecture enables async processing
5. **Idempotency**: Built-in support for idempotent operations
6. **Maintainability**: Clear domain boundaries and responsibilities

## Testing

```python
# Easy to test with mock repositories
def test_create_job():
    mock_repo = Mock(spec=TranslationJobRepository)
    mock_repo.find_by_idempotency_key.return_value = None
    
    service = TranslationDomainService(mock_session_factory)
    job = service.create_translation_job("test.txt", user_id=1)
    
    assert job.filename == "test.txt"
    mock_repo.add.assert_called_once()
```

## Best Practices

1. **Always use UoW for write operations** to ensure consistency
2. **Publish domain events** for cross-domain communication
3. **Use repositories** instead of direct database access
4. **Implement idempotency** for critical operations
5. **Keep domain services focused** on single responsibility
6. **Test with mocked repositories** for fast unit tests

## Future Enhancements

- [ ] Add caching layer to repositories
- [ ] Implement CQRS for read/write separation
- [ ] Add event sourcing for audit trail
- [ ] Integrate with message queue (RabbitMQ/Kafka)
- [ ] Add distributed tracing
- [ ] Implement saga pattern for distributed transactions