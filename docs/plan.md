# Backend Refactoring Plan

## Executive Summary
This plan integrates the original TODO items with expert recommendations to create a robust, maintainable backend architecture. The refactoring addresses critical issues including transaction boundaries, missing abstractions, and production readiness while maintaining backward compatibility.

## ✅ Completed Work

### Phase 1: Repository Pattern + Unit of Work + Domain Events [2025-09-03]
**Implemented Components:**
- Unit of Work Pattern: Transaction management with automatic commit/rollback
- Repository Pattern: Abstract data access layer for all domains
- Domain Events: Event-driven architecture with outbox pattern
- Domain Services: Business logic encapsulation
- Idempotency Support: Prevent duplicate operations
- Dependency Injection: FastAPI dependencies for clean integration

**Key Files:**
- `backend/domains/` - Complete domain structure
- `backend/models/outbox.py` - Outbox event table
- Migration: `5e0cb3120dcb` - Outbox events table

### Phase 2: Configuration Management + Storage Abstraction [2025-09-03]
**Implemented Components:**
- Centralized configuration with Pydantic Settings (`backend/config/`)
- Environment-specific configurations (dev/prod/test)
- Storage abstraction layer (`backend/domains/shared/storage.py`)
- LocalStorage implementation with security features
- Dependency injection for storage
- Updated main.py to use settings

**Key Files:**
- `backend/config/settings.py` - Centralized configuration
- `backend/domains/shared/storage.py` - Storage abstraction
- `backend/dependencies_storage.py` - Storage DI

### Phase 3: Task Queue with Celery + Task Management [2025-09-03]
**Implemented Components:**
- Celery configuration with Redis broker (`backend/celery_app.py`)
- Task execution tracking table (`backend/models/task_execution.py`)
- Migrated all background tasks to Celery (`backend/celery_tasks/`)
- Task monitoring API endpoints (`/api/v1/tasks/`)
- Automatic retry with exponential backoff
- Real-time progress tracking
- Queue prioritization by task type

**Key Files:**
- `backend/celery_app.py` - Celery configuration
- `backend/celery_tasks/` - All Celery tasks
- `backend/api/v1/tasks.py` - Task monitoring endpoints
- Migration: `31c08441cdc2` - Task execution table

### Phase 3.5: Schema Organization [2025-09-03]
**Implemented Components:**
- Refactored monolithic `schemas.py` (354 lines) into organized modules
- Created domain-specific schema files for better maintainability
- Maintained full backward compatibility with existing imports
- Clear separation of concerns by domain

**New Structure:**
- `backend/schemas/base.py` - Shared base classes and utilities
- `backend/schemas/user.py` - User, Announcement, UsageLog schemas
- `backend/schemas/job.py` - TranslationJob schemas
- `backend/schemas/community.py` - Post, Comment, Category schemas
- `backend/schemas/translation.py` - Translation, validation, post-edit schemas
- `backend/schemas/task_execution.py` - Celery task tracking schemas
- `backend/schemas/__init__.py` - Re-exports all schemas for compatibility

## Current State Analysis

### Remaining Issues to Address
- **Legacy code**: `models_old.py` and `schemas.py.bak` still present
- **Missing components**: No `illustrations_tasks.py` implementation
- **Mixed datetime handling**: Timezone-aware and naive datetimes
- **Security concerns**: Admin authentication via header only
- **Database optimization**: Large JSON columns in translation_segments
- **Missing indexes**: Some performance-critical indexes not yet added

## Quick Wins - Immediate Fixes

### Fix Now (Low Effort, High Impact)
1. **Create missing illustrations task**
   - Implement as Celery task in `backend/celery_tasks/illustrations.py`
   - Add progress tracking and retry logic

2. **Pydantic v2 consistency**
   - Switch all models to `model_config = ConfigDict(from_attributes=True)`
   - Centralize datetime serialization

3. **Clean up legacy code**
   - Remove `models_old.py`
   - Remove `schemas.py.bak` (after confirming stability)
   - Remove unused imports and dead code

## Remaining Phases

### Phase 4: Domain-Driven Design with Policy Layer
**Priority: HIGH - Do Fourth**

#### 4.1 Domain Structure
```
backend/domains/
├── shared/
│   ├── __init__.py
│   ├── uow.py              ✅ Completed
│   ├── events.py           ✅ Completed
│   ├── storage.py          ✅ Completed
│   └── exceptions.py
├── translation/
│   ├── __init__.py
│   ├── models.py           # Use existing backend/models/translation.py
│   ├── repository.py       ✅ Completed
│   ├── service.py          ✅ Completed
│   ├── schemas.py          # Use backend/schemas/translation.py
│   ├── routes.py           # Refactor from api/v1/
│   └── tasks.py            # Use backend/celery_tasks/translation.py
├── community/
│   ├── __init__.py
│   ├── models.py           # Use existing backend/models/community.py
│   ├── repository.py
│   ├── service.py
│   ├── policy.py           # NEW: Permission logic
│   ├── schemas.py          # Use backend/schemas/community.py
│   └── routes.py           # Refactor from api/v1/community.py
├── user/
│   ├── __init__.py
│   ├── models.py           # Use existing backend/models/user.py
│   ├── repository.py
│   ├── service.py
│   ├── schemas.py          # Use backend/schemas/user.py
│   └── routes.py
└── admin/
    ├── __init__.py
    ├── policy.py           # NEW: RBAC logic
    ├── schemas.py
    └── routes.py
```

#### Goals:
- Complete domain structure migration (partially done)
- Implement policy layer for authorization
- Extract business logic from endpoints
- Link existing schemas to domains (✅ schemas already organized)

#### Tasks:
- [x] Create shared domain components (UoW, Events, Storage)
- [x] Organize schemas by domain
- [ ] Move routes to respective domains
- [ ] Create policy layer for authorization
- [ ] Move remaining repositories to domains
- [ ] Extract business logic from endpoints to services
- [ ] Create admin domain with RBAC
- [ ] Update imports across codebase
- [ ] Ensure backward compatibility

### Phase 5: Testing Infrastructure
**Priority: HIGH**
**Estimated Time: 1-2 weeks**

#### Goals:
- Achieve >80% test coverage for critical paths
- Set up CI/CD pipeline
- Implement contract testing for repositories

#### Tasks:
- [ ] Set up pytest with async support
- [ ] Create test database fixtures
- [ ] Implement repository contract tests
- [ ] Add service tests with mocked dependencies
- [ ] Create API integration tests
- [ ] Add migration tests
- [ ] Implement policy tests
- [ ] Set up code coverage reporting
- [ ] Add pre-commit hooks
- [ ] Configure GitHub Actions CI

### Phase 6: Error Handling & Observability
**Priority: MEDIUM**
**Estimated Time: 1 week**

#### Goals:
- Implement comprehensive error handling
- Add structured logging
- Set up monitoring and alerting

#### Tasks:
- [ ] Create custom exception hierarchy
- [ ] Implement global exception handler
- [ ] Add structured logging with context
- [ ] Implement request ID tracking
- [ ] Add performance metrics logging
- [ ] Integrate Sentry for error tracking
- [ ] Add OpenTelemetry instrumentation
- [ ] Create monitoring dashboards

### Phase 7: API Improvements
**Priority: MEDIUM**
**Estimated Time: 1 week**

#### Goals:
- Implement proper API versioning
- Add rate limiting
- Improve API documentation

#### Tasks:
- [ ] Implement proper API versioning strategy
- [ ] Add comprehensive OpenAPI documentation
- [ ] Implement rate limiting with Redis
- [ ] Add request validation middleware
- [ ] Implement response caching
- [ ] Add API key management for external consumers
- [ ] Create deprecation strategy

### Phase 8: Performance Optimizations
**Priority: LOW**
**Estimated Time: 1 week**

#### Goals:
- Optimize database queries
- Implement caching strategy
- Reduce response times

#### Tasks:
- [ ] Add critical database indexes
- [ ] Implement eager loading strategies
- [ ] Migrate large JSON columns to separate tables
- [ ] Add Redis caching layer
- [ ] Optimize connection pooling
- [ ] Implement query result caching
- [ ] Add performance monitoring

### Phase 9: Security Hardening
**Priority: LOW**
**Estimated Time: 1 week**

#### Goals:
- Implement comprehensive security measures
- Add vulnerability scanning
- Implement RBAC properly

#### Tasks:
- [ ] Implement file type validation with magic bytes
- [ ] Add virus scanning for uploads
- [ ] Replace admin header secret with proper RBAC
- [ ] Implement rate limiting per user
- [ ] Add SQL injection prevention
- [ ] Implement CSRF protection
- [ ] Add security headers middleware
- [ ] Set up regular security audits

### Phase 10: Documentation
**Priority: LOW**
**Estimated Time: 1 week**

#### Goals:
- Complete technical documentation
- Create operational runbooks
- Document architecture decisions

#### Tasks:
- [ ] Write comprehensive API documentation
- [ ] Create architecture decision records (ADRs)
- [ ] Write development guide
- [ ] Create deployment guide
- [ ] Add code style guide
- [ ] Create contribution guidelines
- [ ] Document configuration options
- [ ] Add troubleshooting guide

## Migration Strategy

### Data Migration Plan
1. **Transaction Segments**: Migrate from JSON column to separate table
2. **Illustration Data**: Move to object storage with DB pointers
3. **UTC Timestamps**: Standardize all datetime fields
4. **Add Missing Indexes**: Apply performance indexes

### Backward Compatibility
- Maintain existing API endpoints during transition
- Use feature flags for gradual rollout
- Version new endpoints as `/api/v2/`
- Provide migration scripts for existing data

## Success Metrics

### Technical Metrics
- **Test Coverage**: >80% for critical paths
- **Response Time**: <200ms for most endpoints
- **Error Rate**: <0.1% for API calls
- **Task Success Rate**: >99% for background jobs

### Code Quality Metrics
- **Cyclomatic Complexity**: <10 per function
- **Code Duplication**: <5%
- **Type Coverage**: 100% with mypy strict
- **Linting**: Zero violations with ruff

### Operational Metrics
- **Deployment Frequency**: Daily capability
- **Mean Time to Recovery**: <30 minutes
- **Change Failure Rate**: <5%
- **Lead Time for Changes**: <1 day

## Timeline Summary

### Completed (3 days actual)
- ✅ Phase 1: Repository Pattern + UoW + Events
- ✅ Phase 2: Configuration + Storage
- ✅ Phase 3: Celery Integration
- ✅ Phase 3.5: Schema Organization

### Remaining Work (6-8 weeks estimated)
- Phase 4: Domain-Driven Design (1-2 weeks)
- Phase 5: Testing Infrastructure (1-2 weeks)
- Phase 6: Error Handling & Observability (1 week)
- Phase 7: API Improvements (1 week)
- Phase 8-10: Performance, Security, Documentation (2-3 weeks)

**Total Estimated Completion**: 6-8 weeks from now

## Next Steps

### Immediate Actions (This Week)
1. Implement quick wins (illustrations task, cleanup)
2. Begin Phase 4: Domain-Driven Design
3. Start writing tests for completed phases

### Short Term (Next 2-3 Weeks)
1. Complete Phase 4 and 5
2. Deploy to staging environment
3. Begin performance testing

### Medium Term (4-6 Weeks)
1. Complete Phases 6-7
2. Production deployment preparation
3. Team training on new architecture

### Long Term (6-8 Weeks)
1. Complete all remaining phases
2. Full production deployment
3. Decommission legacy code

## Risk Mitigation

### Technical Risks
- **Data Loss**: Comprehensive backups before each migration
- **Performance Degradation**: Load test each phase
- **Breaking Changes**: Maintain compatibility layer
- **Task Failures**: Celery retry mechanism already implemented

### Process Risks
- **Scope Creep**: Strict phase boundaries
- **Timeline Slippage**: Buffer time per phase
- **Knowledge Transfer**: Documentation being updated continuously
- **Testing Gaps**: Mandatory test coverage before phase completion

## Conclusion

With Phases 1-3.5 completed, we have established a solid foundation with proper transaction management, configuration, storage abstraction, task queue infrastructure, and organized schemas. The refactoring has addressed critical architectural issues:

- ✅ Transaction boundaries with Unit of Work pattern
- ✅ Centralized configuration management  
- ✅ Storage abstraction for cloud readiness
- ✅ Robust task queue with Celery
- ✅ Organized schemas by domain (previously 354-line monolith)

The remaining phases focus on completing the domain-driven design, adding comprehensive testing, and production hardening. The architecture is now significantly more maintainable and scalable, with clear separation of concerns and proper abstraction layers. Phase 4 (Domain-Driven Design) is partially complete with shared components and organized schemas already in place.