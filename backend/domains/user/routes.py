"""User domain API routes - thin routing layer."""

import os
from typing import List, Optional

from fastapi import Depends, HTTPException, Header, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from svix import Webhook
import asyncio
import json

from backend.config import SessionLocal
from backend.config.dependencies import get_db, get_required_user
from backend.domains.user.models import User
from backend.domains.user.schemas import (
    User as UserSchema,
    Announcement as AnnouncementSchema,
    UserCreate,
    UserUpdate,
    TokenUsageDashboard,
    ApiConfiguration,
    ApiConfigurationUpdate,
)
from backend.domains.user.service import UserService
from backend.domains.user.repository import SqlAlchemyUserRepository


CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """Dependency to get user service."""
    return UserService(db)


async def get_current_user(
    current_user: User = Depends(get_required_user)
) -> UserSchema:
    """Get the current user's profile."""
    return UserSchema.from_orm(current_user)


async def list_announcements(
    service: UserService = Depends(get_user_service)
) -> List[AnnouncementSchema]:
    """Get active announcements (public endpoint)."""
    announcements = service.get_announcements(active_only=True)
    return [AnnouncementSchema.from_orm(a) for a in announcements]


async def stream_announcements():
    """Stream announcements via Server-Sent Events (SSE)."""
    async def event_generator():
        while True:
            try:
                with SessionLocal() as session:
                    service = UserService(session)
                    announcements = service.get_announcements(active_only=True)
                    announcements_data = [AnnouncementSchema.from_orm(a).dict() for a in announcements]
                
                # Send as SSE event
                yield f"data: {json.dumps(announcements_data)}\n\n"
                
                # Wait 30 seconds before next update
                await asyncio.sleep(30)
            except Exception as e:
                # Send error event
                yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        }
    )


async def handle_clerk_webhook(
    request: Request,
    svix_id: str = Header(None),
    svix_timestamp: str = Header(None),
    svix_signature: str = Header(None),
    db: Session = Depends(get_db)
):
    """Handle Clerk webhook events for user management."""
    if not CLERK_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="Webhook secret is not configured.")
    
    headers = {
        "svix-id": svix_id,
        "svix-timestamp": svix_timestamp,
        "svix-signature": svix_signature,
    }
    
    try:
        payload_body = await request.body()
        wh = Webhook(CLERK_WEBHOOK_SECRET)
        evt = wh.verify(payload_body, headers)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error verifying webhook signature: {e}")
    
    event_type = evt["type"]
    data = evt["data"]
    
    if event_type == "user.created":
        user_name = f'{data.get("first_name", "")} {data.get("last_name", "")}'.strip()
        email_addresses = data.get("email_addresses", [])
        email_address = email_addresses[0].get("email_address") if email_addresses else None
        
        user_in = UserCreate(
            clerk_user_id=data["id"],
            email=email_address or None,
            name=user_name or None
        )
        repo = SqlAlchemyUserRepository(db)
        db_user = User(clerk_user_id=user_in.clerk_user_id, email=user_in.email, name=user_in.name)
        db.add(db_user)
        db.commit()
        
    elif event_type == "user.updated":
        clerk_user_id = data["id"]
        repo = SqlAlchemyUserRepository(db)
        db_user = repo.get_by_clerk_id(clerk_user_id)
        
        user_name = f'{data.get("first_name", "")} {data.get("last_name", "")}'.strip()
        email_addresses = data.get("email_addresses", [])
        email_address = email_addresses[0].get("email_address") if email_addresses else None
        
        if db_user:
            user_update = UserUpdate(email=email_address or None, name=user_name or None)
            for key, value in user_update.dict(exclude_unset=True).items():
                setattr(db_user, key, value)
            db.commit()
        else:
            print(f"--- [INFO] Webhook received user.updated for non-existent user {clerk_user_id}. Creating them now. ---")
            user_in = UserCreate(
                clerk_user_id=clerk_user_id,
                email=email_address or None,
                name=user_name or None
            )
            db_user = User(clerk_user_id=user_in.clerk_user_id, email=user_in.email, name=user_in.name)
            db.add(db_user)
            db.commit()
            
    elif event_type == "user.deleted":
        repo = SqlAlchemyUserRepository(db)
        db_user = repo.get_by_clerk_id(data["id"])
        if db_user:
            db.delete(db_user)
            db.commit()

    return {"status": "success"}


async def get_token_usage(
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service),
) -> TokenUsageDashboard:
    """Return the authenticated user's token usage summary."""
    summary = service.get_token_usage_dashboard(current_user.id)
    return TokenUsageDashboard.model_validate(summary)


async def get_api_configuration(
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service),
) -> ApiConfiguration:
    """Get the authenticated user's API configuration."""
    config = service.get_api_configuration(current_user.id)
    return ApiConfiguration.model_validate(config)


async def update_api_configuration(
    config: ApiConfigurationUpdate,
    current_user: User = Depends(get_required_user),
    service: UserService = Depends(get_user_service),
) -> ApiConfiguration:
    """Update the authenticated user's API configuration."""
    update_data = config.model_dump(exclude_unset=True)
    updated_config = await service.update_api_configuration(
        user_id=current_user.id,
        **update_data,
    )
    return ApiConfiguration.model_validate(updated_config)
