# Domain Decoupling Migration Guide

## Overview
This guide explains how to migrate existing code from direct User model dependencies to the new decoupled architecture using interfaces and events.

## Migration Steps

### Step 1: Update Import Statements

**Before:**
```python
from backend.domains.user.models import User
```

**After:**
```python
from backend.domains.shared.interfaces import UserContext, IUserProvider
from backend.domains.translation.user_provider import TranslationUserProvider
```

### Step 2: Update Service Constructors

**Before:**
```python
class TranslationService:
    def __init__(self, session: AsyncSession):
        self.session = session
```

**After:**
```python
class TranslationService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_provider = TranslationUserProvider(session)
        self.event_publisher = EventPublisher(session)
```

### Step 3: Update Method Signatures

**Before:**
```python
async def create_job(self, job_data: JobCreate, user: User):
    job = TranslationJob(
        owner_id=user.id,
        owner=user,  # Direct relationship
        ...
    )
```

**After:**
```python
async def create_job(self, job_data: JobCreate, user_context: UserContext):
    job = TranslationJob(
        owner_id=user_context.id,  # Just the ID
        ...
    )
    # No direct relationship assignment
```

### Step 4: Update Permission Checks

**Before:**
```python
if user.role == "admin" or job.owner_id == user.id:
    # Allow access
```

**After:**
```python
permissions = UserPermissions(user_context)
if permissions.can_access_job(job.owner_id):
    # Allow access
```

### Step 5: Add Event Publishing

**Before:**
```python
async def complete_translation(self, job_id: int):
    job.status = "COMPLETED"
    await self.session.commit()
```

**After:**
```python
async def complete_translation(self, job_id: int):
    job.status = "COMPLETED"
    
    # Publish domain event
    await self.event_publisher.publish_translation_completed(
        job_id=job_id,
        user_id=job.owner_id,
        filename=job.filename,
        ...
    )
    
    await self.session.commit()
```

### Step 6: Update Authentication

**Before:**
```python
from backend.auth import get_current_user

@router.post("/jobs")
async def create_job(
    user: User = Depends(get_current_user)
):
    ...
```

**After:**
```python
from backend.auth import get_current_user_context

@router.post("/jobs")
async def create_job(
    user_context: UserContext = Depends(get_current_user_context)
):
    ...
```

## Authentication Helper Update

Create a new authentication helper that returns UserContext:

```python
# backend/auth.py

from backend.domains.shared.interfaces import UserContext, UserContextAdapter

async def get_current_user_context(
    user: User = Depends(get_current_user)
) -> UserContext:
    """Convert User model to UserContext."""
    return UserContextAdapter.to_context(user)
```

## Repository Pattern Updates

**Before:**
```python
class TranslationRepository:
    async def get_user_jobs(self, user: User):
        return await self.session.execute(
            select(TranslationJob)
            .options(joinedload(TranslationJob.owner))
            .where(TranslationJob.owner_id == user.id)
        )
```

**After:**
```python
class TranslationRepository:
    async def get_user_jobs(self, user_id: int):
        return await self.session.execute(
            select(TranslationJob)
            .where(TranslationJob.owner_id == user_id)
        )
    
    async def get_job_with_owner(self, job_id: int):
        job = await self.get_job(job_id)
        if job and job.owner_id:
            owner_context = await self.user_provider.get_user_context(job.owner_id)
            return job, owner_context
        return job, None
```

## Testing Updates

**Before:**
```python
def test_create_job():
    user = User(id=1, email="test@example.com", role="user")
    job = service.create_job(data, user)
```

**After:**
```python
def test_create_job():
    user_context = UserContext(
        id=1,
        clerk_id="clerk_123",
        email="test@example.com",
        role="user"
    )
    job = service.create_job(data, user_context)
```

## Gradual Migration Strategy

### Phase 1: Add Adapters (Backward Compatible)
1. Keep existing User model references
2. Add UserContextAdapter to convert between User and UserContext
3. Add event publishing alongside existing code

### Phase 2: Update Services
1. Update service methods to accept UserContext
2. Remove direct User model imports from services
3. Use user providers for user data access

### Phase 3: Update Routes
1. Update route handlers to use UserContext
2. Update authentication dependencies
3. Remove User model from API responses

### Phase 4: Remove Direct Relationships
1. Remove relationship definitions from models
2. Use repositories for cross-domain queries
3. Rely on events for cross-domain communication

## Common Pitfalls and Solutions

### Pitfall 1: Circular Imports
**Problem:** Importing User model in domain services creates circular dependencies.
**Solution:** Use lazy imports in user providers or dependency injection.

### Pitfall 2: Missing User Data
**Problem:** UserContext doesn't have all User model fields.
**Solution:** Extend UserContext for domain-specific needs or fetch additional data through providers.

### Pitfall 3: Transaction Boundaries
**Problem:** Events published before transaction commit might reference uncommitted data.
**Solution:** Use outbox pattern - events are saved in same transaction and processed later.

### Pitfall 4: Performance Issues
**Problem:** N+1 queries when fetching user data for multiple entities.
**Solution:** Implement batch loading in user providers:

```python
async def get_users_by_ids(self, user_ids: List[int]) -> List[UserContext]:
    # Fetch all users in one query
    users = await self.session.execute(
        select(User).where(User.id.in_(user_ids))
    )
    return [UserContextAdapter.to_context(u) for u in users]
```

## Verification Checklist

- [ ] No direct imports of User model in domain services
- [ ] All user data access goes through IUserProvider
- [ ] Events are published for significant state changes
- [ ] Permission checks use UserPermissions class
- [ ] Tests use UserContext instead of User model
- [ ] API responses don't expose internal User model
- [ ] Outbox events are being processed by Celery task
- [ ] No circular import errors
- [ ] All tests pass

## Rollback Plan

If issues arise during migration:

1. **Keep backward compatibility layer:**
   ```python
   # Temporary adapter that accepts both User and UserContext
   def adapt_user(user_or_context):
       if isinstance(user_or_context, UserContext):
           return user_or_context
       return UserContextAdapter.to_context(user_or_context)
   ```

2. **Use feature flags:**
   ```python
   if settings.USE_DECOUPLED_ARCHITECTURE:
       return await decoupled_service.create_job(data, user_context)
   else:
       return await legacy_service.create_job(data, user)
   ```

3. **Maintain parallel implementations** until confident in new architecture

## Benefits After Migration

1. **Reduced Coupling:** Domains can evolve independently
2. **Better Testability:** Mock UserContext instead of complex User model
3. **Event-Driven:** Automatic notifications and metrics through events
4. **Microservice Ready:** Domains can be extracted to separate services
5. **Clear Boundaries:** Explicit contracts between domains

## Next Steps

1. Start with non-critical services for practice
2. Update one domain at a time
3. Run both old and new code in parallel initially
4. Monitor event processing and performance
5. Remove legacy code once stable