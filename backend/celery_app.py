"""
Celery configuration for background task processing.
"""
from celery import Celery
from celery.signals import setup_logging
from .config import get_settings
import logging

# Get settings
settings = get_settings()

# Create Celery app
celery_app = Celery(
    "translation_system",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.celery_tasks.translation",
        "backend.celery_tasks.validation",
        "backend.celery_tasks.post_edit",
        "backend.celery_tasks.illustrations",
        "backend.celery_tasks.event_processor",
        "backend.celery_tasks.backup_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour hard limit
    task_soft_time_limit=3000,  # 50 min soft limit
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    
    # Retry configuration
    task_autoretry_for=(Exception,),
    task_retry_kwargs={'max_retries': 3, 'countdown': 60},
    task_retry_backoff=True,
    task_retry_backoff_max=600,
    task_retry_jitter=True,
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    
    # Beat schedule for periodic tasks
    beat_schedule={
        'process-outbox-events': {
            'task': 'backend.celery_tasks.event_processor.process_outbox_events',
            'schedule': 30.0,  # Every 30 seconds
        },
        'cleanup-temp-files': {
            'task': 'backend.celery_tasks.maintenance.cleanup_temp_files',
            'schedule': 3600.0,  # Every hour
        },
        'backup-database-daily': {
            'task': 'backup.database_to_s3',
            'schedule': 86400.0,  # Every 24 hours (daily)
            'options': {
                'queue': 'maintenance',
                'priority': 1,
            }
        },
    },
    
    # Worker configuration
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
    worker_disable_rate_limits=False,
    
    # Routing
    task_routes={
        'backend.celery_tasks.translation.*': {'queue': 'translation'},
        'backend.celery_tasks.validation.*': {'queue': 'validation'},
        'backend.celery_tasks.post_edit.*': {'queue': 'post_edit'},
        'backend.celery_tasks.illustrations.*': {'queue': 'illustrations'},
        'backend.celery_tasks.event_processor.*': {'queue': 'events'},
        'backend.celery_tasks.maintenance.*': {'queue': 'maintenance'},
        'backup.*': {'queue': 'maintenance'},
    },
    
    # Queue configuration
    task_default_queue='default',
    task_queues={
        'default': {
            'exchange': 'default',
            'exchange_type': 'direct',
            'routing_key': 'default',
        },
        'translation': {
            'exchange': 'translation',
            'exchange_type': 'direct', 
            'routing_key': 'translation',
            'priority': 5,
        },
        'validation': {
            'exchange': 'validation',
            'exchange_type': 'direct',
            'routing_key': 'validation', 
            'priority': 3,
        },
        'post_edit': {
            'exchange': 'post_edit',
            'exchange_type': 'direct',
            'routing_key': 'post_edit',
            'priority': 3,
        },
        'illustrations': {
            'exchange': 'illustrations',
            'exchange_type': 'direct',
            'routing_key': 'illustrations',
            'priority': 2,
        },
        'events': {
            'exchange': 'events',
            'exchange_type': 'direct',
            'routing_key': 'events',
            'priority': 10,
        },
        'maintenance': {
            'exchange': 'maintenance',
            'exchange_type': 'direct',
            'routing_key': 'maintenance',
            'priority': 1,
        },
    },
)


@setup_logging.connect
def config_loggers(*args, **kwargs):
    """Configure logging for Celery."""
    from logging.config import dictConfig
    
    dictConfig({
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default': {
                'format': '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
            },
            'json': {
                'class': 'pythonjsonlogger.jsonlogger.JsonFormatter',
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            }
        },
        'handlers': {
            'console': {
                'level': settings.log_level,
                'class': 'logging.StreamHandler',
                'formatter': 'json' if settings.log_format == 'json' else 'default',
            },
            'file': {
                'level': settings.log_level,
                'class': 'logging.FileHandler',
                'filename': settings.log_file or 'celery.log',
                'formatter': 'json' if settings.log_format == 'json' else 'default',
            } if settings.log_file else {},
        },
        'root': {
            'level': settings.log_level,
            'handlers': ['console'] + (['file'] if settings.log_file else []),
        },
    })


# Export celery app
__all__ = ['celery_app']