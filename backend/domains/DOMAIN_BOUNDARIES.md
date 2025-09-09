# Domain Boundaries Documentation

## Overview
This document defines the clear boundaries between domains and identifies shared vs domain-specific models to reduce coupling.

## Domain Classifications

### Core Domains
1. **Translation Domain**
   - Purpose: Handle translation processing, validation, and post-editing
   - Models: TranslationJob, TranslationUsageLog
   - Dependencies: User (for ownership)

2. **Community Domain**
   - Purpose: Manage community features (posts, comments, announcements)
   - Models: Post, Comment, PostCategory, Announcement
   - Dependencies: User (for authorship)

3. **User Domain**
   - Purpose: Manage user accounts and authentication
   - Models: User
   - Dependencies: None (root domain)

### Shared Infrastructure
1. **Base Models**
   - Purpose: Provide common ORM infrastructure
   - Components: Base, mixins, common fields

2. **Task Execution**
   - Purpose: Track background task execution
   - Models: TaskExecution
   - Used by: All domains for async operations

3. **Event System**
   - Purpose: Enable domain event-driven communication
   - Models: OutboxEvent
   - Used by: All domains for decoupled communication

## Current Coupling Issues

### Direct Model References
1. **TranslationJob → User**: Direct foreign key relationship
   - Issue: Translation domain knows about User model structure
   - Solution: Use UserContext interface

2. **Post/Comment → User**: Direct foreign key relationships
   - Issue: Community domain depends on User model
   - Solution: Use UserContext interface

3. **User → TranslationJob/Post/Comment**: Back-references via relationships
   - Issue: User model knows about all domains
   - Solution: Remove back-references, use repositories for queries

## Proposed Decoupling Strategy

### 1. User Context Interfaces
Create interfaces that expose only necessary user information to each domain:

```python
# Shared interface
class UserContext:
    id: int
    clerk_id: str
    email: Optional[str]
    name: Optional[str]
    role: str
```

### 2. Domain Events
Replace direct coupling with event-driven communication:

- **TranslationCompleted**: Emitted when translation finishes
- **UserCreated**: Emitted when new user registers
- **PostCreated**: Emitted when new post is created
- **CommentAdded**: Emitted when comment is added

### 3. Repository Pattern
Use repositories to manage cross-domain queries without model dependencies:

```python
# Instead of user.jobs relationship
jobs = await translation_repo.get_jobs_by_user(user_id)

# Instead of user.posts relationship
posts = await community_repo.get_posts_by_user(user_id)
```

## Implementation Phases

### Phase 1: Define Interfaces
- Create UserContext interface
- Create domain event contracts
- Define value objects for data transfer

### Phase 2: Update Domain Services
- Replace User model imports with UserContext
- Update repositories to use interfaces
- Implement event publishing

### Phase 3: Remove Direct Relationships
- Remove back-references from User model
- Update queries to use repositories
- Test all endpoints

## Benefits of Decoupling

1. **Independent Development**: Domains can evolve independently
2. **Testability**: Easier to test domains in isolation
3. **Scalability**: Domains can be split into microservices later
4. **Maintainability**: Clear boundaries reduce complexity
5. **Event Sourcing Ready**: Event-driven architecture enables event sourcing

## Migration Strategy

1. **Backward Compatibility**: Keep existing relationships during migration
2. **Gradual Migration**: Update one domain at a time
3. **Feature Flags**: Use flags to toggle between old/new implementations
4. **Monitoring**: Track events and ensure no data loss

## Success Metrics

- No direct imports between domain models
- All cross-domain communication via events or interfaces
- Domain services only depend on shared interfaces
- Tests can run without other domain models