"""
Backend schemas package - re-exports all schema classes for backward compatibility.

This package now imports from domain-specific schema modules but maintains
the same interface for backward compatibility.
"""

# Import from new domain locations
# Base schemas from shared domain
from backend.domains.shared.schemas import (
    KSTTimezoneBase,
    UTC_ZONE,
    KST_ZONE,
    TaskStatus,
    TaskKind,
    TaskExecutionResponse,
    TaskExecutionListResponse,
    TaskStatsResponse,
)

# User domain schemas
from backend.domains.user.schemas import (
    UserBase,
    UserCreate,
    UserUpdate,
    User,
    TranslationUsageLogBase,
    TranslationUsageLogCreate,
    TranslationUsageLog,
    AnnouncementBase,
    AnnouncementCreate,
    Announcement,
)

# Translation domain schemas
from backend.domains.translation.schemas import (
    TranslationJobBase,
    TranslationJobCreate,
    TranslationJob,
    GlossaryTerm,
    StyleAnalysisResponse,
    GlossaryAnalysisResponse,
    ValidationRequest,
    PostEditRequest,
    PostEditSegment,
    StructuredPostEditLog,
    StructuredValidationReport,
)

# Community domain schemas
from backend.domains.community.schemas import (
    PostCategoryBase,
    PostCategoryCreate,
    PostCategory,
    PostBase,
    PostCreate,
    PostUpdate,
    PostList,
    Post,
    CommentBase,
    CommentCreate,
    CommentUpdate,
    Comment,
)

# Re-export core schemas that are used (these come from core package)
from core.schemas import (
    ValidationCase,
    ValidationResponse,
    ExtractedTerms,
    TranslatedTerms,
    TranslatedTerm,
    CharacterInteraction,
    DialogueAnalysisResult,
    NarrativeStyleDefinition,
    StyleDeviation,
)

# Update forward references after all imports are complete
# Need to rebuild models with circular dependencies
from backend.domains.user.schemas import User
from backend.domains.community.schemas import Comment, Post, PostList

# Force rebuild to resolve forward references
Comment.model_rebuild()
Post.model_rebuild() 
PostList.model_rebuild()

# Export all schemas
__all__ = [
    # Base
    'KSTTimezoneBase',
    'UTC_ZONE',
    'KST_ZONE',
    # User
    'UserBase',
    'UserCreate',
    'UserUpdate',
    'User',
    'TranslationUsageLogBase',
    'TranslationUsageLogCreate',
    'TranslationUsageLog',
    'AnnouncementBase',
    'AnnouncementCreate',
    'Announcement',
    # Job
    'TranslationJobBase',
    'TranslationJobCreate',
    'TranslationJob',
    # Community
    'PostCategoryBase',
    'PostCategoryCreate',
    'PostCategory',
    'PostBase',
    'PostCreate',
    'PostUpdate',
    'PostList',
    'Post',
    'CommentBase',
    'CommentCreate',
    'CommentUpdate',
    'Comment',
    # Translation
    'GlossaryTerm',
    'StyleAnalysisResponse',
    'GlossaryAnalysisResponse',
    'ValidationRequest',
    'PostEditRequest',
    'PostEditSegment',
    'StructuredPostEditLog',
    'StructuredValidationReport',
    'ValidationCase',
    'ValidationResponse',
    'ExtractedTerms',
    'TranslatedTerms',
    'TranslatedTerm',
    'CharacterInteraction',
    'DialogueAnalysisResult',
    'NarrativeStyleDefinition',
    'StyleDeviation',
    # Task execution
    'TaskStatus',
    'TaskKind',
    'TaskExecutionResponse',
    'TaskExecutionListResponse',
    'TaskStatsResponse',
]