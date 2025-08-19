# Backend Architecture

## Overview
The backend has been refactored from a monolithic 1387-line `main.py` file into a clean, modular architecture following the separation of concerns principle. The translation API module has been further decomposed from a single 522-line file into 5 focused modules for better maintainability.

## Directory Structure

```
backend/
├── api/v1/                     # API Layer - HTTP request handling
│   ├── translation.py          # Router aggregator for translation APIs
│   ├── analysis.py            # Style and glossary analysis endpoints
│   ├── jobs.py                # Translation job CRUD operations
│   ├── downloads.py           # File downloads and content retrieval
│   ├── validation_routes.py   # Translation validation endpoints
│   ├── post_edit_routes.py    # Post-editing endpoints
│   ├── community.py           # Community board endpoints  
│   ├── admin.py              # Admin management endpoints
│   ├── webhooks.py           # Webhook handlers (Clerk)
│   └── announcements.py      # SSE streaming endpoints
│
├── services/                   # Business Logic Layer
│   ├── translation_service.py  # Translation business logic
│   ├── validation_service.py   # Validation logic
│   ├── post_edit_service.py   # Post-editing logic
│   ├── community_service.py   # Community features logic
│   └── announcement_service.py # Announcement management
│
├── background_tasks/           # Async Task Layer
│   ├── translation_tasks.py   # Background translation jobs
│   ├── validation_tasks.py    # Background validation
│   └── post_edit_tasks.py     # Background post-editing
│
├── core/                       # Core translation engine (unchanged)
│   ├── translation/           # Translation components
│   ├── config/               # Configuration management
│   └── prompts/              # AI prompt templates
│
├── models/                    # SQLAlchemy models package
│   ├── _base.py              # Base declarative class
│   ├── user.py               # User model
│   ├── translation.py        # Translation job models
│   ├── community.py          # Community models
│   └── __init__.py           # Model exports
│
├── migrations/                # Alembic migrations
│   ├── env.py                # Alembic environment
│   ├── script.py.mako        # Migration template
│   └── versions/             # Migration versions
│
├── alembic.ini               # Alembic configuration
├── dependencies.py            # Shared FastAPI dependencies
├── schemas.py                # Pydantic schemas
├── crud.py                   # Database operations
├── auth.py                   # Authentication logic
├── database.py               # Database connection
├── auto_init.py              # Auto-initialization
└── main.py                   # Slim entry point (~80 lines)
```

## Architecture Layers

### 1. API Layer (`api/v1/`)
- **Responsibility**: Handle HTTP requests/responses
- **Components**: FastAPI routers organized by domain
- **Key Features**:
  - Input validation
  - HTTP status codes
  - Response formatting
  - Route definitions

### 2. Service Layer (`services/`)
- **Responsibility**: Business logic and orchestration
- **Components**: Domain-specific service classes
- **Key Features**:
  - Business rule enforcement
  - Data transformation
  - Cross-cutting concerns
  - Reusable logic

### 3. Background Task Layer (`background_tasks/`)
- **Responsibility**: Async processing
- **Components**: Task functions for long-running operations
- **Key Features**:
  - Translation processing
  - Validation runs
  - Post-editing operations
  - Database session management

### 4. Data Access Layer
- **Components**: `crud.py`, `models.py`, `database.py`
- **Responsibility**: Database operations and ORM

## Benefits of New Architecture

1. **Separation of Concerns**
   - Each layer has a single, well-defined responsibility
   - Business logic separated from HTTP handling
   - Database operations isolated in CRUD layer

2. **Improved Testability**
   - Service layer can be unit tested independently
   - Mock dependencies easily
   - Test business logic without HTTP layer

3. **Better Maintainability**
   - Smaller, focused files (~200-400 lines each)
   - Clear module boundaries
   - Easy to locate and modify specific functionality

4. **Enhanced Reusability**
   - Services can be used in different contexts (API, CLI, workers)
   - Shared logic centralized in service layer
   - Common dependencies in single module

5. **Scalability**
   - Easy to add new endpoints without modifying existing code
   - Can split into microservices if needed
   - Background tasks can be moved to separate workers

## API Endpoint Organization

### Translation API (`/api/v1/`)
The translation endpoints are organized into logical modules for better maintainability:

#### Analysis Endpoints (`analysis.py`)
- **POST** `/analyze-style` - Analyze narrative style
- **POST** `/analyze-glossary` - Extract glossary terms

#### Job Management (`jobs.py`)
- **GET** `/jobs` - List all translation jobs for current user
- **POST** `/jobs` - Create translation job (upload file)
- **GET** `/jobs/{id}` - Get job details and status
- **DELETE** `/jobs/{id}` - Delete translation job

#### Downloads & Content (`downloads.py`)
- **GET** `/download/{id}` - Download translated file (legacy)
- **GET** `/jobs/{id}/output` - Download translated file
- **GET** `/jobs/{id}/logs/{type}` - Download debug logs
- **GET** `/jobs/{id}/glossary` - Get final glossary
- **GET** `/jobs/{id}/segments` - Get segmented translation data
- **GET** `/jobs/{id}/content` - Get translated content as text

#### Validation (`validation_routes.py`)
- **PUT** `/jobs/{id}/validation` - Trigger validation
- **GET** `/jobs/{id}/validation-report` - Get validation report

#### Post-Editing (`post_edit_routes.py`)
- **PUT** `/jobs/{id}/post-edit` - Trigger post-editing
- **GET** `/jobs/{id}/post-edit-log` - Get post-edit log

### Community API (`/api/v1/community/`)
- Category management
- Post CRUD operations
- Comment system
- Image uploads
- Privacy controls

### Admin API (`/api/v1/admin/`)
- Announcement management
- Category initialization
- System administration

### Webhooks (`/api/v1/webhooks/`)
- Clerk user synchronization
- External service integration

### Announcements (`/api/v1/announcements/`)
- Server-Sent Events streaming
- Real-time announcement updates

## Database Management

### Models Organization
The SQLAlchemy models are organized into a package structure:
- `models/_base.py`: Contains the declarative Base class
- `models/user.py`: User authentication and profile models
- `models/translation.py`: Translation job and usage log models
- `models/community.py`: Community features (posts, comments, categories)

### Migration System (Alembic)
Database schema changes are managed using Alembic:
```bash
# Apply all migrations
cd backend && alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# View migration history
alembic history

# Rollback to previous version
alembic downgrade -1
```

The migration system supports both SQLite (development) and PostgreSQL (production) transparently.

## Migration from Old Structure

The refactoring maintains 100% backward compatibility:
- All API endpoints remain at the same URLs
- Request/response formats unchanged
- Database schema managed via Alembic migrations
- Frontend requires no modifications

## Development Guidelines

1. **Adding New Features**
   - Create service in `services/` for business logic
   - Add router in `api/v1/` for endpoints
   - Use `dependencies.py` for shared deps
   - Add background task if needed

2. **Testing**
   - Unit test services independently
   - Integration test API endpoints
   - Mock external dependencies

3. **Error Handling**
   - Services raise domain exceptions
   - API layer converts to HTTP errors
   - Consistent error response format

## Running the Application

```bash
# Development
uvicorn backend.main:app --reload --port 8000

# Production
uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

## Environment Variables

Required environment variables remain unchanged:
- `DATABASE_URL`: PostgreSQL connection string
- `CLERK_WEBHOOK_SECRET`: Clerk webhook verification
- `ADMIN_SECRET_KEY`: Admin endpoint authentication
- `GEMINI_API_KEY`: Default API key for validation/post-edit