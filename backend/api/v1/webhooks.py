"""Webhook API endpoints."""

import os
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from svix import Webhook

from ...dependencies import get_db
from ...domains.user import schemas
from ...domains.user.models import User
from ...domains.user.repository import SqlAlchemyUserRepository


router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])


CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")


@router.post("/clerk")
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
        
        user_in = schemas.UserCreate(
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
            user_update = schemas.UserUpdate(email=email_address or None, name=user_name or None)
            for key, value in user_update.dict(exclude_unset=True).items():
                setattr(db_user, key, value)
            db.commit()
        else:
            print(f"--- [INFO] Webhook received user.updated for non-existent user {clerk_user_id}. Creating them now. ---")
            user_in = schemas.UserCreate(
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