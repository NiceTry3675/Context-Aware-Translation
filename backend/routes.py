"""Consolidated API router for all domain endpoints."""

from fastapi import APIRouter
from typing import List

# Import domain route modules
from backend.domains.translation import routes as translation
from backend.domains.validation import routes as validation
from backend.domains.post_edit import routes as post_edit
from backend.domains.community import routes as community
from backend.domains.user import routes as user
from backend.domains.admin import routes as admin
from backend.domains.tasks import routes as tasks
from backend.domains.export import routes as export_routes
from backend.domains.analysis import routes as analysis
from backend.domains.illustrations import routes as illustrations

# Import schemas for response models
from backend.domains.translation.schemas import TranslationJob
from backend.domains.validation.schemas import StructuredValidationReport
from backend.domains.post_edit.schemas import StructuredPostEditLog
from backend.domains.community.schemas import Post, Comment, PostCategory, CategoryOverview
from backend.domains.user.schemas import User, Announcement
from backend.domains.tasks.schemas import TaskExecutionResponse, TaskExecutionListResponse, TaskStatsSimple
from backend.domains.analysis.schemas import StyleAnalysisResponse, GlossaryAnalysisResponse, CharacterAnalysisResponse

# Create main API router
router = APIRouter(prefix="/api/v1")

# Translation endpoints
router.add_api_route(
    "/jobs", 
    translation.list_jobs, 
    methods=["GET"],
    response_model=List[TranslationJob],
    tags=["jobs"]
)
router.add_api_route(
    "/jobs", 
    translation.create_job, 
    methods=["POST"],
    response_model=TranslationJob,
    tags=["jobs"]
)
router.add_api_route(
    "/jobs/{job_id}", 
    translation.get_job, 
    methods=["GET"],
    response_model=TranslationJob,
    tags=["jobs"]
)
router.add_api_route(
    "/jobs/{job_id}", 
    translation.delete_job, 
    methods=["DELETE"],
    status_code=204,
    tags=["jobs"]
)
router.add_api_route(
    "/jobs/{job_id}/content", 
    translation.get_job_content, 
    methods=["GET"],
    tags=["jobs"]
)
router.add_api_route(
    "/jobs/{job_id}/segments", 
    translation.get_job_segments, 
    methods=["GET"],
    tags=["jobs"]
)

# Validation endpoints
router.add_api_route(
    "/validate/{job_id}", 
    validation.validate_job, 
    methods=["POST"],
    tags=["validation"]
)
router.add_api_route(
    "/validation/{job_id}/status", 
    validation.get_validation_status, 
    methods=["GET"],
    tags=["validation"]
)

# Post-edit endpoints
router.add_api_route(
    "/post-edit/{job_id}", 
    post_edit.post_edit_job, 
    methods=["POST"],
    tags=["post-edit"]
)
router.add_api_route(
    "/post-edit/{job_id}/status", 
    post_edit.get_post_edit_status, 
    methods=["GET"],
    tags=["post-edit"]
)

# Export endpoints
router.add_api_route(
    "/download/{job_id}", 
    export_routes.download_file, 
    methods=["GET"],
    tags=["export"]
)
router.add_api_route(
    "/export/{job_id}", 
    export_routes.export_job, 
    methods=["POST"],
    tags=["export"]
)

# Analysis endpoints
router.add_api_route(
    "/analysis/style", 
    analysis.analyze_style, 
    methods=["POST"],
    response_model=StyleAnalysisResponse,
    tags=["analysis"]
)
router.add_api_route(
    "/analysis/glossary", 
    analysis.analyze_glossary, 
    methods=["POST"],
    response_model=GlossaryAnalysisResponse,
    tags=["analysis"]
)
router.add_api_route(
    "/analysis/characters", 
    analysis.analyze_characters, 
    methods=["POST"],
    response_model=CharacterAnalysisResponse,
    tags=["analysis"]
)

# Include illustrations router with all its routes
router.include_router(illustrations.router)

# Include tasks router with all its routes
router.include_router(tasks.router)

# Community endpoints
router.add_api_route(
    "/community/categories",
    community.list_categories,
    methods=["GET"],
    response_model=List[PostCategory],
    tags=["community"]
)
router.add_api_route(
    "/community/categories/overview",
    community.list_categories_overview,
    methods=["GET"],
    response_model=List[CategoryOverview],
    tags=["community"]
)
router.add_api_route(
    "/posts", 
    community.list_posts, 
    methods=["GET"],
    response_model=List[Post],
    tags=["community"]
)
router.add_api_route(
    "/posts", 
    community.create_post, 
    methods=["POST"],
    response_model=Post,
    tags=["community"]
)
router.add_api_route(
    "/posts/{post_id}", 
    community.get_post, 
    methods=["GET"],
    response_model=Post,
    tags=["community"]
)
router.add_api_route(
    "/posts/{post_id}/comments",
    community.create_comment,
    methods=["POST"],
    response_model=Comment,
    tags=["community"]
)

# User endpoints
router.add_api_route(
    "/users/me", 
    user.get_current_user, 
    methods=["GET"],
    response_model=User,
    tags=["users"]
)
router.add_api_route(
    "/announcements", 
    user.list_announcements, 
    methods=["GET"],
    response_model=List[Announcement],
    tags=["users"]
)
router.add_api_route(
    "/announcements/stream", 
    user.stream_announcements, 
    methods=["GET"],
    tags=["users"]
)

# Admin endpoints
router.add_api_route(
    "/admin/posts/{post_id}", 
    admin.delete_any_post, 
    methods=["DELETE"],
    status_code=204,
    tags=["admin"]
)
router.add_api_route(
    "/admin/announcements", 
    admin.create_announcement, 
    methods=["POST"],
    response_model=Announcement,
    tags=["admin"]
)

# Webhooks
router.add_api_route(
    "/webhooks/clerk", 
    user.handle_clerk_webhook, 
    methods=["POST"],
    include_in_schema=False  # Don't expose webhook in OpenAPI schema
)
