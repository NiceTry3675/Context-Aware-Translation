# Backend Architecture

## Overview

FastAPI-based REST API with domain-driven design. Uses Celery for distributed task processing and PostgreSQL for persistence.

## Current Architecture

```
backend/
├── api/v1/                    # Thin routing layer
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
│   ├── logging_config.py    # Structured logging
│   └── settings.py          # Pydantic settings
│
├── domains/                   # Business logic (DDD)
│   ├── shared/              # Cross-cutting concerns
│   │   ├── analysis/        # Style, glossary, character analysis
│   │   ├── base/           # Base classes, model factory
│   │   ├── utils/          # File management
│   │   ├── events.py       # Domain events
│   │   ├── repository.py   # Base repository
│   │   ├── storage.py      # Storage abstraction
│   │   └── uow.py         # Unit of Work
│   │
│   ├── translation/          # Translation domain
│   │   ├── service.py       # Main translation service
│   │   ├── validation_service.py  # Validation logic
│   │   ├── post_edit_service.py   # Post-edit logic
│   │   ├── repository.py    # Data access
│   │   └── routes.py        # Domain routing
│   │
│   ├── community/            # Community domain
│   │   ├── service.py       # Community logic
│   │   ├── repository.py    # Data access
│   │   └── routes.py        # Domain routing
│   │
│   └── user/                # User domain
│       ├── service.py       # User & announcements
│       ├── repository.py    # Data access
│       └── routes.py        # Domain routing
│
├── models/                    # SQLAlchemy ORM
│   ├── _base.py             # Base model
│   ├── community.py         # Community models
│   ├── outbox.py           # Event sourcing
│   ├── task_execution.py   # Task tracking
│   ├── translation.py      # Translation models
│   └── user.py             # User models
│
├── schemas/                   # Pydantic DTOs
│   ├── base.py              # Base schemas
│   ├── community.py         # Community DTOs
│   ├── core_schemas.py      # Core translation schemas
│   ├── jobs.py              # Job DTOs
│   ├── task_execution.py   # Task DTOs
│   └── webhooks.py         # Webhook schemas
│
├── tasks/                     # Celery background tasks
│   ├── base.py              # Base task classes
│   ├── celery_app.py        # Celery configuration
│   ├── event_processor.py   # Event processing
│   ├── post_edit.py         # Post-edit tasks
│   ├── translation.py       # Translation tasks
│   └── validation.py        # Validation tasks
│
├── migrations/               # Alembic migrations
├── auth.py                  # Clerk authentication
├── database.py             # Database configuration
└── main.py                 # FastAPI application
```

## Core Components

### 1. API Layer (`/api/v1/`)
- **Purpose**: HTTP routing and request/response handling
- **Responsibilities**: Validation, serialization, auth enforcement
- **Pattern**: Thin controllers delegating to domain services

### 2. Domain Layer (`/domains/`)
- **Purpose**: Core business logic using DDD principles
- **Structure**:
  ```
  domain/
  ├── service.py       # Business operations
  ├── repository.py    # Data access
  └── routes.py        # Domain-specific routing
  ```
- **Shared Modules**:
  - `analysis/`: Style, glossary, character analysis
  - `base/`: ServiceBase, ModelAPIFactory
  - `utils/`: FileManager utilities
  - `storage.py`: Pluggable storage backends
  - `uow.py`: Transaction management
  - `events.py`: Domain event system

### 3. Task Processing (`/tasks/`)
- **Technology**: Celery with Redis broker
- **Queues**: translation, validation, post_edit, events, default
- **Features**:
  - Automatic retry with exponential backoff
  - Progress tracking via `update_state()`
  - Database-backed execution history
  - Priority queue routing

### 4. Storage Abstraction
```python
# Pluggable backends
storage = get_storage(settings)
await storage.save_file(path, content)
async for chunk in storage.open_file(path):
    process(chunk)
```
- **Backends**: LocalStorage, S3Storage (planned), GCSStorage (planned)
- **Security**: Path traversal protection, type validation

## Data Flow

### Translation Pipeline
```
Client Request → API Endpoint → Domain Service → Celery Task → Core Engine
       ↓              ↓              ↓              ↓            ↓
   Validation    Job Creation    Repository    Progress     Results
                                    ↓           Updates     Storage
                                 Database         ↓            ↓
                                              Task Status   Response
```

### Event Processing
```
Domain Operation → Domain Event → Outbox Storage → Event Processor
                                       ↓                ↓
                                  Transaction      Celery Beat
                                                        ↓
                                                  Event Dispatch
```

## Database Schema

### Core Tables
- `users`: Clerk user mapping
- `translation_jobs`: Job tracking with status enum
- `task_executions`: Celery execution history
- `posts`, `comments`: Community content
- `announcements`: Admin announcements
- `outbox_events`: Domain events for async processing

## Authentication

### Three Levels
1. **Public**: Read-only community endpoints
2. **User**: Clerk JWT required (translation, posting)
3. **Admin**: ADMIN_SECRET_KEY header required

## Task Monitoring

### Endpoints
- GET `/api/v1/tasks/{id}`: Task status with progress
- GET `/api/v1/tasks/`: List with filters
- POST `/api/v1/tasks/{id}/cancel`: Cancel task

### Tools
- Celery Flower: Web UI at `:5555`
- Database: `task_executions` table
- Logs: Structured JSON with correlation IDs

## Performance Optimizations

- **Database**: Connection pooling, eager loading, indexed FKs
- **Async**: File I/O, external APIs, streaming large files
- **Caching**: Redis for session data (query cache planned)
- **Queues**: Priority routing, worker concurrency

## Security

- **Input**: Pydantic validation, file type whitelist
- **Files**: Path traversal protection, size limits
- **API**: CORS config, JWT validation, rate limiting (planned)
- **Storage**: Presigned URLs for cloud backends

## Migration Status

### ✅ Completed (2025-01-05)
- Domain-driven architecture implementation
- Service layer removal and consolidation
- Celery integration with task tracking
- Storage abstraction layer
- Configuration management
- Unit of Work pattern
- Domain event system

### 🔄 In Progress
- CRUD to repository pattern migration
- Event sourcing completion

### 📋 Planned
- Caching layer implementation
- S3/GCS storage backends
- GraphQL API
- Rate limiting

## Development Guidelines

### Adding Features
1. Define domain model/schema
2. Update repository methods
3. Implement in domain service
4. Add API endpoint
5. Create Celery task if async
6. Write tests

### Database Changes
```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Task Implementation
```python
class MyTask(TrackedTask):
    def run(self, job_id):
        # Automatic tracking, retry, progress
        self.update_state(state='PROGRESS', meta={'progress': 50})
        return result
```

---
*Last Updated: 2025-01-05*  
*Version: 3.0 - Domain-driven architecture*