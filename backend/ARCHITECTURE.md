# Backend Architecture

## Overview
The backend has been refactored from a monolithic 1387-line `main.py` file into a clean, modular architecture following the separation of concerns principle.

## Directory Structure

```
backend/
├── api/v1/                     # API Layer - HTTP request handling
│   ├── translation.py          # Translation endpoints
│   ├── community.py            # Community board endpoints  
│   ├── admin.py               # Admin management endpoints
│   ├── webhooks.py            # Webhook handlers (Clerk)
│   └── announcements.py       # SSE streaming endpoints
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
├── dependencies.py            # Shared FastAPI dependencies
├── models.py                 # SQLAlchemy models
├── schemas.py                # Pydantic schemas
├── crud.py                   # Database operations
├── auth.py                   # Authentication logic
├── database.py               # Database connection
├── migrations.py             # Database migrations
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

### Translation API (`/api/v1/translation/`)
- **POST** `/analyze-style` - Analyze narrative style
- **POST** `/analyze-glossary` - Extract glossary terms
- **POST** `/jobs` - Create translation job (upload file)
- **GET** `/jobs/{id}` - Get job details and status
- **GET** `/jobs/{id}/output` - Download translated file
- **GET** `/jobs/{id}/logs/{type}` - Download debug logs
- **GET** `/jobs/{id}/glossary` - Get final glossary
- **PUT** `/jobs/{id}/validation` - Trigger validation
- **GET** `/jobs/{id}/validation-report` - Get validation report
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

## Migration from Old Structure

The refactoring maintains 100% backward compatibility:
- All API endpoints remain at the same URLs
- Request/response formats unchanged
- Database schema unchanged
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