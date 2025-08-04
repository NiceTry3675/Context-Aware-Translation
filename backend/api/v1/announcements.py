"""Announcement SSE streaming endpoints."""

import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ...database import SessionLocal
from ...services.announcement_service import AnnouncementService


router = APIRouter(prefix="/api/v1/announcements", tags=["announcements"])


async def announcement_generator(request: Request):
    """Generate Server-Sent Events for announcement updates."""
    last_sent_announcement = None
    client_id = id(request)
    print(f"📡 새 클라이언트 연결: {client_id}")
    
    def get_announcement_from_db():
        with SessionLocal() as db:
            return AnnouncementService.get_active_announcement(db)
    
    try:
        # Send initial announcement if exists
        current_announcement = get_announcement_from_db()
        if current_announcement:
            yield AnnouncementService.format_announcement_for_sse(current_announcement)
            last_sent_announcement = current_announcement
            print(f"📤 초기 공지 전송 (클라이언트 {client_id}): ID {current_announcement.id}")
    except Exception as e:
        print(f"❌ 초기 공지 전송 오류: {e}")
    
    # Main loop for streaming updates
    while True:
        if await request.is_disconnected():
            print(f"🔌 클라이언트 연결 해제: {client_id}")
            break
        
        try:
            current_announcement = get_announcement_from_db()
            
            # Check if we should send an update
            if AnnouncementService.should_send_announcement_update(current_announcement, last_sent_announcement):
                # Determine if announcement was deactivated
                if current_announcement is None and last_sent_announcement is not None:
                    # Send deactivation message
                    yield AnnouncementService.format_announcement_for_sse(last_sent_announcement, is_active=False)
                    print(f"🔇 공지 비활성화 전송 (클라이언트 {client_id})")
                    last_sent_announcement = None
                elif current_announcement is not None:
                    # Send new or updated announcement
                    yield AnnouncementService.format_announcement_for_sse(current_announcement)
                    print(f"📢 새 공지/변경 전송 (클라이언트 {client_id}): ID {current_announcement.id}")
                    last_sent_announcement = current_announcement
                    
        except Exception as e:
            print(f"❌ SSE 스트림 오류 (클라이언트 {client_id}): {e}")
        
        # Wait before checking for updates again
        await asyncio.sleep(120)


@router.get("/stream")
async def stream_announcements(request: Request):
    """Stream announcements via Server-Sent Events."""
    return StreamingResponse(
        announcement_generator(request),
        media_type="text/event-stream; charset=utf-8"
    )