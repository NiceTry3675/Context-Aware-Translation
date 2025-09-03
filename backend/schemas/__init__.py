"""
Backend schemas package - re-exports all schema classes for backward compatibility.
"""

# Base schemas
from .base import KSTTimezoneBase, UTC_ZONE, KST_ZONE

# User schemas
from .user import (
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

# Job schemas
from .job import (
    TranslationJobBase,
    TranslationJobCreate,
    TranslationJob,
)

# Community schemas
from .community import (
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

# Translation schemas
from .translation import (
    GlossaryTerm,
    StyleAnalysisResponse,
    GlossaryAnalysisResponse,
    ValidationRequest,
    PostEditRequest,
    PostEditSegment,
    StructuredPostEditLog,
    StructuredValidationReport,
    # Re-export core schemas that are used
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

# Task execution schemas
from .task_execution import (
    TaskStatus,
    TaskKind,
    TaskExecutionResponse,
    TaskExecutionListResponse,
    TaskStatsResponse,
)

# Update forward references after all imports are complete
Comment.model_rebuild()
Post.model_rebuild()

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