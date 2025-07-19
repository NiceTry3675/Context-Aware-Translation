import os
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from clerk_backend_api import Clerk
from clerk_backend_api.models import ClerkErrors, SDKError
from clerk_backend_api.security import AuthenticateRequestOptions
from typing import Optional

# Internal imports
from . import crud, models, schemas
from .database import SessionLocal

# Initialize the Clerk client.
clerk = Clerk()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_user_claims(request: Request) -> Optional[dict]:
    """
    A FastAPI dependency that verifies the Clerk JWT if present.
    Returns the token payload if the user is signed in, otherwise returns None.
    Does not raise an exception for unauthenticated users.
    """
    # Check if the Authorization header exists before proceeding
    if "Authorization" not in request.headers:
        return None
        
    try:
        options = AuthenticateRequestOptions(secret_key=os.environ.get("CLERK_SECRET_KEY"))
        request_state = clerk.authenticate_request(request=request, options=options)

        return request_state.payload if request_state.is_signed_in else None

    except (ClerkErrors, SDKError):
        # This can happen if the token is present but invalid (e.g., expired).
        # We treat this as an unauthenticated state for this optional check.
        return None
    except Exception as e:
        print(f"--- [AUTH DEBUG] An unexpected error occurred during optional auth check: {e} ---")
        # For unexpected errors, we might still want to deny access or just log it.
        # Returning None is safer to prevent accidental access on system failure.
        return None

async def get_required_user(
    claims: dict = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Dependency that requires a user to be authenticated.
    It ensures a user exists in our database for the given Clerk JWT claims.
    If the user doesn't exist, it creates them.
    Raises an exception if the user is not authenticated.
    """
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Clerk user ID (sub) not found in token.")

    db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)

    if not db_user:
        print(f"--- [INFO] User with Clerk ID {clerk_user_id} not found in DB. Creating new user record from API request. ---")
        
        email_address = claims.get('primary_email_address')
        # Clerk might provide first_name and last_name separately
        first_name = claims.get('clerk_first_name') or ''
        last_name = claims.get('clerk_last_name') or ''
        name = f"{first_name} {last_name}".strip()

        new_user_data = schemas.UserCreate(
            clerk_user_id=clerk_user_id,
            email=email_address,
            name=name if name else None
        )
        db_user = crud.create_user(db, user=new_user_data)
        print(f"--- [INFO] Successfully created user {db_user.id} for Clerk ID {clerk_user_id}. ---")

    return db_user

async def get_optional_user(
    claims: Optional[dict] = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Dependency that provides the user model if authenticated, but doesn't fail if not.
    Returns the user model instance or None.
    """
    if not claims:
        return None

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        return None # Or raise an error if a token is present but malformed

    db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)
    
    # Optional: You could still create the user here if they exist in Clerk but not your DB
    if not db_user:
        print(f"--- [INFO] Optional auth: User with Clerk ID {clerk_user_id} not found in DB. Proceeding as anonymous. ---")
        # In this optional scenario, we won't create a user automatically.
        # We'll let the required endpoints handle user creation.
        return None

    return db_user