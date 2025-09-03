# Backend Architecture

## Overview

FastAPI-based REST API serving as the bridge between the frontend application and the core translation engine. Uses Celery for distributed task processing and PostgreSQL for data persistence.

## Current Architecture

```
backend/
├── api/v1/                    # API endpoints (routing layer)
│   ├── admin.py              # Admin operations
│   ├── analysis.py           # Translation analysis
│   ├── announcements.py      # Site announcements
│   ├── community.py          # Community features
│   ├── downloads.py          # File downloads
│   ├── illustrations.py      # AI illustration generation
│   ├── jobs.py               # Job management
│   ├── post_edit_routes.py   # Post-editing
│   ├── schemas.py            # Schema exports
│   ├── tasks.py              # Task monitoring
│   ├── translation.py        # Legacy translation
│   ├── validation_routes.py  # Translation validation
│   └── webhooks.py           # External integrations
│
├── config/                    # Configuration management
│   ├── __init__.py
│   ├── logging_config.py    # Structured logging
│   └── settings.py          # Pydantic settings
│
├── domains/                   # Domain-driven design layer
│   ├── shared/              # Shared infrastructure
│   │   ├── events.py       # Domain events
│   │   ├── repository.py   # Base repository
│   │   ├── storage.py      # Storage abstraction
│   │   └── uow.py         # Unit of Work
│   │
│   ├── translation/          # Translation domain
│   │   ├── models.py        # SQLAlchemy models
│   │   ├── repository.py    # Data access
│   │   ├── schemas.py       # Pydantic schemas
│   │   └── service.py       # Business logic
│   │
│   ├── community/            # Community domain
│   │   ├── models.py
│   │   ├── repository.py
│   │   ├── schemas.py
│   │   └── service.py
│   │
│   └── user/                # User domain
│       ├── models.py
│       ├── repository.py
│       ├── schemas.py
│       └── service.py
│
├── models/                    # Database models
│   ├── _base.py             # Base model
│   ├── community.py         # Community models
│   ├── outbox.py           # Event sourcing
│   ├── task_execution.py   # Task tracking
│   ├── translation.py      # Translation models
│   └── user.py             # User models
│
├── schemas/                   # API schemas (Pydantic)
│   ├── base.py              # Base schemas
│   ├── community.py         # Community DTOs
│   ├── core_schemas.py      # Core translation schemas
│   ├── jobs.py              # Job DTOs
│   ├── task_execution.py   # Task DTOs
│   └── webhooks.py         # Webhook schemas
│
├── services/                  # Business services
│   ├── announcement_service.py     # Announcement logic
│   ├── community_service.py        # Community logic
│   ├── glossary_analysis_service.py # Term extraction
│   ├── pdf_generator.py           # PDF export
│   ├── post_edit_service.py       # Post-editing
│   ├── style_analysis_service.py  # Style analysis
│   ├── translation_service.py     # Translation orchestration
│   └── validation_service.py      # Quality checking
│
├── tasks/                     # Celery tasks
│   ├── base.py              # Base task classes
│   ├── celery_app.py        # Celery configuration
│   ├── event_processor.py   # Event processing
│   ├── post_edit.py         # Post-edit tasks
│   ├── translation.py       # Translation tasks
│   └── validation.py        # Validation tasks
│
├── background_tasks/          # DEPRECATED - Legacy wrappers
│   └── [legacy files]       # To be removed
│
├── migrations/               # Alembic database migrations
│   └── versions/            # Migration files
│
├── auth.py                  # Authentication (Clerk)
├── celery_app.py           # Celery re-export
├── crud.py                 # Legacy CRUD operations
├── database.py             # Database configuration
├── dependencies.py         # Dependency injection
└── main.py                 # FastAPI application
```

## Core Components

### 1. API Layer (`/api/v1/`)
- **Purpose**: HTTP routing and request/response handling
- **Responsibilities**: 
  - Route definitions
  - Request validation
  - Response serialization
  - Authentication enforcement
- **Pattern**: Thin controllers delegating to services

### 2. Domain Layer (`/domains/`)
- **Purpose**: Core business logic using DDD principles
- **Components**:
  - **Models**: Domain entities
  - **Repository**: Data access abstraction
  - **Service**: Business operations
  - **Schemas**: Data transfer objects
- **Pattern**: Repository pattern with Unit of Work

### 3. Task Processing (`/tasks/`)
- **Purpose**: Asynchronous job processing
- **Technology**: Celery with Redis broker
- **Features**:
  - Automatic retry with exponential backoff
  - Progress tracking
  - Database-backed execution history
  - Priority queue routing
- **Queues**: translation, validation, post_edit, events, default

### 4. Service Layer (`/services/`)
- **Purpose**: Business logic orchestration
- **Responsibilities**:
  - Integration with core translation engine
  - File processing
  - Report generation
  - External API coordination

### 5. Storage Abstraction (`/domains/shared/storage.py`)
- **Purpose**: Unified file storage interface
- **Backends**: 
  - LocalStorage (filesystem)
  - S3Storage (planned)
  - GCSStorage (planned)
- **Features**: Path security, async operations

## Data Flow

### Translation Request Flow
1. **Request**: Client → API endpoint
2. **Validation**: Pydantic schema validation
3. **Job Creation**: Store in database with "processing" status
4. **Task Queue**: Launch Celery task
5. **Processing**: Task executes with core engine
6. **Progress**: Updates via task.update_state()
7. **Completion**: Update job status, store results
8. **Response**: Client polls for completion

### Event Processing
1. **Domain Event**: Created during business operations
2. **Outbox Storage**: Persisted transactionally
3. **Event Processor**: Periodic Celery beat task
4. **Event Dispatch**: Route to appropriate handlers
5. **Cleanup**: Remove processed events

## Database Schema

### Core Tables
- **users**: User accounts (Clerk integration)
- **translation_jobs**: Main job tracking
- **translation_usage_logs**: API usage metrics
- **illustration_jobs**: Image generation
- **posts/comments**: Community content
- **announcements**: Admin announcements
- **task_executions**: Celery task history
- **outbox_events**: Domain events

## Configuration

### Environment-Based Settings
- Development: Local SQLite, verbose logging
- Production: PostgreSQL, structured JSON logging
- Testing: In-memory database, minimal logging

### Storage Configuration
- Local: Filesystem with path validation
- Cloud: S3/GCS with presigned URLs
- Security: File type validation, size limits

## Authentication & Authorization

### Public Access
- GET community endpoints
- Webhook endpoints (signature validated)

### User Authentication (Clerk JWT)
- Translation operations
- Content creation
- Personal data access

### Admin Authentication
- ADMIN_SECRET_KEY header
- Full system access

## Monitoring & Observability

### Logging
- Structured JSON format
- Correlation IDs for request tracing
- Performance metrics

### Task Monitoring
- `/api/v1/tasks/` endpoints
- Celery Flower web UI
- Database-backed execution history

### Health Checks
- Database connectivity
- Redis availability
- Storage accessibility

## Performance Optimizations

### Database
- Connection pooling
- Eager loading for relationships
- Indexed foreign keys

### Caching
- Redis for session data
- Query result caching (planned)

### Async Operations
- File I/O operations
- External API calls
- Database queries (where supported)

## Security Measures

### Input Validation
- Pydantic schema enforcement
- File type whitelisting
- Request size limits

### File Security
- Path traversal prevention
- Filename sanitization
- Virus scanning (planned)

### API Security
- Rate limiting (planned)
- CORS configuration
- HTTPS enforcement (production)

## Migration Status

### Completed
- ✅ Celery integration
- ✅ Task execution tracking
- ✅ Storage abstraction
- ✅ Configuration management
- ✅ Domain structure setup

### In Progress
- 🔄 CRUD to repository migration
- 🔄 Service consolidation
- 🔄 Removing legacy code

### Planned
- 📋 Complete DDD implementation
- 📋 Event sourcing completion
- 📋 Caching layer
- 📋 GraphQL API (future)

## Development Guidelines

### Adding New Features
1. Define domain model if needed
2. Create/update repository methods
3. Implement service logic
4. Add API endpoint
5. Create Celery task if async
6. Write tests
7. Update documentation

### Database Changes
1. Modify SQLAlchemy models
2. Generate migration: `alembic revision --autogenerate`
3. Review and apply: `alembic upgrade head`

### Task Implementation
1. Extend `TrackedTask` base class
2. Implement error handling and retries
3. Add progress tracking
4. Update task routing in celery_app.py

---
*Last Updated: 2025-09-03*
*Version: 2.0 - Post-refactoring architecture*