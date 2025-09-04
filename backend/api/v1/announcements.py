"""Announcement SSE streaming endpoints - thin router layer."""

from fastapi import APIRouter

# Re-export the stream endpoint from domain router for backward compatibility
from ...domains.user.routes import stream_announcements

router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])

# Add the stream endpoint from domain with proper path
router.add_api_route(
    "/stream",
    stream_announcements,
    methods=["GET"],
    summary="Stream announcements via Server-Sent Events"
)