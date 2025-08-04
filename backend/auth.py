import os
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from clerk_backend_api import Clerk
from clerk_backend_api.models import ClerkErrors, SDKError
from clerk_backend_api.security import AuthenticateRequestOptions
from typing import Optional

# Internal imports
from . import crud, models, schemas
from .database import SessionLocal

# Initialize the Clerk client with proper API key.
clerk = Clerk(bearer_auth=os.environ.get("CLERK_SECRET_KEY"))

async def get_clerk_user_info(clerk_user_id: str) -> dict:
    """Clerk Management API를 사용하여 완전한 사용자 정보 가져오기"""
    try:
        user = clerk.users.get(user_id=clerk_user_id)
        
        # Clerk User 객체에서 정보 추출
        user_info = {
            'id': user.id,
            'email': None,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': None,
            'username': user.username,
            'image_url': user.image_url,
            'public_metadata': user.public_metadata or {}  # publicMetadata 추가
        }
        
        # Primary email 찾기
        if user.email_addresses:
            for email_addr in user.email_addresses:
                if hasattr(email_addr, 'id') and email_addr.id == user.primary_email_address_id:
                    user_info['email'] = email_addr.email_address
                    break
            # Primary를 못 찾으면 첫 번째 이메일 사용
            if not user_info['email'] and user.email_addresses:
                user_info['email'] = user.email_addresses[0].email_address
        
        # 전체 이름 구성
        if user.first_name or user.last_name:
            user_info['full_name'] = f"{user.first_name or ''} {user.last_name or ''}".strip()
        
        print(f"--- [DEBUG] Clerk API User Info: {user_info}")
        return user_info
        
    except Exception as e:
        print(f"--- [ERROR] Failed to get Clerk user info for {clerk_user_id}: {e}")
        return None

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
        print(f"--- [AUTH DEBUG] No Authorization header found in request to {request.url.path}")
        return None
    
    auth_header = request.headers.get("Authorization")
    print(f"--- [AUTH DEBUG] Authorization header for {request.url.path}: {auth_header[:50] if auth_header else 'None'}...")
        
    try:
        clerk_secret = os.environ.get("CLERK_SECRET_KEY")
        if not clerk_secret:
            print("--- [AUTH ERROR] CLERK_SECRET_KEY not found in environment variables!")
            return None
        print(f"--- [AUTH DEBUG] Using Clerk secret key: {clerk_secret[:10]}...")
        
        options = AuthenticateRequestOptions(secret_key=clerk_secret)
        request_state = clerk.authenticate_request(request=request, options=options)

        if request_state.is_signed_in:
            payload = request_state.payload
            print(f"--- [DEBUG] Full JWT Claims: {payload}")
            print(f"--- [DEBUG] Available keys: {list(payload.keys()) if payload else 'None'}")
            return payload
        else:
            print(f"--- [AUTH DEBUG] Token present but not signed in. Request state: {request_state}")
        return None

    except (ClerkErrors, SDKError) as e:
        # This can happen if the token is present but invalid (e.g., expired).
        # We treat this as an unauthenticated state for this optional check.
        print(f"--- [AUTH DEBUG] Clerk authentication error: {e}")
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
        try:
            # Clerk Management API를 사용하여 완전한 사용자 정보 가져오기
            clerk_user_info = await get_clerk_user_info(clerk_user_id)
            
            if clerk_user_info:
                email_address = clerk_user_info.get('email')
                name = (clerk_user_info.get('username') or 
                       clerk_user_info.get('full_name') or
                       (email_address.split('@')[0] if email_address else None))
            else:
                # Fallback to JWT claims if API fails
                email_address = claims.get('primary_email_address') or claims.get('email')
                name = (claims.get('name') or claims.get('full_name') or 
                       f"{claims.get('first_name', '')} {claims.get('last_name', '')}".strip() or
                       (email_address.split('@')[0] if email_address else None))

            new_user_data = schemas.UserCreate(
                clerk_user_id=clerk_user_id,
                email=email_address,
                name=name
            )
            db_user = crud.create_user(db, user=new_user_data)
            print(f"--- [INFO] Successfully created user {db_user.id} for Clerk ID {clerk_user_id} with name: {name}. ---")
        except IntegrityError:
            db.rollback()
            print(f"--- [WARN] Race condition detected for Clerk ID {clerk_user_id}. User likely created by webhook. Refetching... ---")
            db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)
            if not db_user:
                # This case is highly unlikely but good to handle.
                raise HTTPException(status_code=500, detail="Failed to create or find user after race condition.")
    else:
        # 기존 사용자의 이름이 없는 경우 업데이트
        if not db_user.name:
            print(f"--- [INFO] Updating existing user {db_user.id} name from None ---")
            
            # Clerk Management API를 사용하여 완전한 사용자 정보 가져오기
            clerk_user_info = await get_clerk_user_info(clerk_user_id)
            
            if clerk_user_info:
                # 사용자명 우선 순위로 변경
                name = (clerk_user_info.get('username') or 
                       clerk_user_info.get('full_name') or
                       (clerk_user_info.get('email').split('@')[0] if clerk_user_info.get('email') else None))
                email_address = clerk_user_info.get('email')
                
                # 이메일도 없는 경우 같이 업데이트
                update_data = {}
                if name:
                    update_data['name'] = name
                if email_address and not db_user.email:
                    update_data['email'] = email_address
                    
                if update_data:
                    user_update = schemas.UserUpdate(**update_data)
                    db_user = crud.update_user(db, clerk_user_id, user_update)
                    print(f"--- [INFO] Updated user {db_user.id} with: {update_data}. ---")

    # Sync user role from Clerk every time they are fetched
    if db_user:
        db_user = await sync_user_role_from_clerk(db, db_user)

    return db_user

async def get_optional_user(
    claims: Optional[dict] = Depends(get_current_user_claims),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """
    Dependency that provides the user model if authenticated, but doesn't fail if not.
    Returns the user model instance or None.
    Creates user if they exist in Clerk but not in our DB.
    """
    if not claims:
        return None

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        return None

    db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)
    
    # If user doesn't exist in DB but is authenticated, create them
    if not db_user:
        print(f"--- [INFO] Optional auth: User with Clerk ID {clerk_user_id} not found in DB. Creating new user. ---")
        try:
            # Clerk Management API를 사용하여 완전한 사용자 정보 가져오기
            clerk_user_info = await get_clerk_user_info(clerk_user_id)
            
            if clerk_user_info:
                email_address = clerk_user_info.get('email')
                name = (clerk_user_info.get('username') or 
                       clerk_user_info.get('full_name') or
                       (email_address.split('@')[0] if email_address else None))
            else:
                # Fallback to JWT claims
                email_address = claims.get('primary_email_address') or claims.get('email')
                name = (claims.get('name') or claims.get('full_name') or 
                       f"{claims.get('first_name', '')} {claims.get('last_name', '')}".strip() or
                       (email_address.split('@')[0] if email_address else None))

            new_user_data = schemas.UserCreate(
                clerk_user_id=clerk_user_id,
                email=email_address,
                name=name
            )
            db_user = crud.create_user(db, user=new_user_data)
            print(f"--- [INFO] Successfully created user {db_user.id} for Clerk ID {clerk_user_id} in optional auth. ---")
        except IntegrityError:
            db.rollback()
            print(f"--- [WARN] Race condition detected for Clerk ID {clerk_user_id} during optional auth. Refetching... ---")
            db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)
        except Exception as e:
            print(f"--- [ERROR] Failed to create user in optional auth: {e}")
            return None

    if db_user:
        db_user = await sync_user_role_from_clerk(db, db_user)

    return db_user

async def sync_user_role_from_clerk(db: Session, db_user: models.User) -> models.User:
    """
    Fetches user role from Clerk's publicMetadata and updates the local DB if they differ.
    """
    try:
        clerk_user_info = await get_clerk_user_info(db_user.clerk_user_id)
        # Return early if no metadata is available
        if not (clerk_user_info and clerk_user_info.get('public_metadata')):
            return db_user

        clerk_role = clerk_user_info['public_metadata'].get('role', 'user')
        
        if db_user.role != clerk_role:
            print(f"--- [INFO] Role mismatch for user {db_user.id}. DB: '{db_user.role}', Clerk: '{clerk_role}'. Syncing... ---")
            db_user.role = clerk_role
            db.commit()
            db.refresh(db_user)
            print(f"--- [INFO] Synced role for user {db_user.id} to '{clerk_role}'. ---")
            
    except Exception as e:
        print(f"--- [WARN] Could not sync user role for {db_user.clerk_user_id}: {e}")
    
    return db_user

async def is_admin(user: models.User) -> bool:
    """
    사용자가 관리자인지 확인
    1. 로컬 데이터베이스의 role 컬럼 확인
    2. Clerk의 publicMetadata 확인
    """
    # 1. 로컬 DB에서 admin이면 바로 True 반환
    if user.role == "admin":
        return True
    
    # 2. Clerk publicMetadata에서 확인
    try:
        clerk_user_info = await get_clerk_user_info(user.clerk_user_id)
        if clerk_user_info and clerk_user_info.get('public_metadata'):
            clerk_role = clerk_user_info['public_metadata'].get('role')
            return clerk_role == 'admin'
    except Exception as e:
        print(f"--- [WARN] Failed to check Clerk metadata for user {user.clerk_user_id}: {e}")
    
    return False

def is_admin_sync(user: models.User) -> bool:
    """
    동기 버전: 사용자가 관리자인지 확인
    주로 CRUD 함수들에서 사용 (로컬 DB만 확인)
    """
    return user.role == "admin"