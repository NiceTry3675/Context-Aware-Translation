"""Webhook API endpoints."""

import os
from fastapi import APIRouter, Request, Header, HTTPException, Depends
from sqlalchemy.orm import Session
from svix import Webhook

from ...dependencies import get_db
from ... import crud, schemas


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
        crud.create_user(db, user=user_in)
        
    elif event_type == "user.updated":
        clerk_user_id = data["id"]
        db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)
        
        user_name = f'{data.get("first_name", "")} {data.get("last_name", "")}'.strip()
        email_addresses = data.get("email_addresses", [])
        email_address = email_addresses[0].get("email_address") if email_addresses else None
        
        if db_user:
            user_update = schemas.UserUpdate(email=email_address or None, name=user_name or None)
            crud.update_user(db, clerk_id=clerk_user_id, user_update=user_update)
        else:
            print(f"--- [INFO] Webhook received user.updated for non-existent user {clerk_user_id}. Creating them now. ---")
            user_in = schemas.UserCreate(
                clerk_user_id=clerk_user_id,
                email=email_address or None,
                name=user_name or None
            )
            crud.create_user(db, user=user_in)
            
    elif event_type == "user.deleted":
        crud.delete_user(db, clerk_id=data["id"])
    
    return {"status": "success"}