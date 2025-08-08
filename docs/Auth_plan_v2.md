### **[Project] Clerk Authentication Integration Plan (v2)**

**1. Goal**

Integrate **Clerk** as the primary authentication service. This will provide a robust user management system and associate translation jobs with specific users, laying the foundation for future features like usage tracking and community functions.

**2. Core Architecture & Data Flow (v2)**

*   **Frontend (Next.js):** Handles all user-facing authentication UI using Clerk's pre-built React components. It acquires a JWT from Clerk and sends it with every authenticated API request to the backend.
*   **Backend (FastAPI):** Validates the JWT from the frontend to protect API endpoints. It will not handle sign-up or password logic directly.
*   **Database (PostgreSQL):** A new `User` table will be added to store application-specific user data. This table will be linked to the existing `TranslationJob` table and kept in sync with Clerk's user data via **Webhooks**.
*   **Clerk Service:** Acts as the central "source of truth" for user identity.

---

### **Part 1: Backend Integration (FastAPI)**

**Objective:** Secure API endpoints by validating JWTs and associating users with their translation jobs.

*   **Step 1.1: Environment & Libraries**
    *   Install the `clerk-python` library: `pip install clerk-python`
    *   In your backend environment (e.g., a `.env` file or Railway environment variables), add the `CLERK_SECRET_KEY` from the Clerk Dashboard.

*   **Step 1.2: Create User Model & Update Job Model**
    *   **Location:** `backend/models.py`
    *   Add the new `User` model and add a foreign key relationship to the `TranslationJob` model.

    ```python
    # In backend/models.py

    from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
    from sqlalchemy.orm import relationship
    from sqlalchemy.sql import func
    from .database import Base

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, index=True)
        clerk_user_id = Column(String, unique=True, index=True, nullable=False)
        email = Column(String, unique=True, index=True, nullable=False)
        name = Column(String, nullable=True)
        created_at = Column(DateTime(timezone=True), server_default=func.now())
        updated_at = Column(DateTime(timezone=True), onupdate=func.now())

        jobs = relationship("TranslationJob", back_populates="owner")

    class TranslationJob(Base):
        __tablename__ = "translation_jobs"

        id = Column(Integer, primary_key=True, index=True)
        # ... (existing columns)
        filepath = Column(String, nullable=True)

        # --- Add these lines ---
        owner_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Start as nullable for existing jobs
        owner = relationship("User", back_populates="jobs")
        # -----------------------

    # ... (rest of the models)
    ```
    *   **Note:** The `models.Base.metadata.create_all(bind=engine)` call in `backend/main.py` will automatically create the `users` table and add the `owner_id` column.

*   **Step 1.3: Create JWT Validation Dependency**
    *   **Location:** Create a new file `backend/auth.py`.
    *   This dependency will verify the token and fetch the `clerk_user_id`.

    ```python
    # In backend/auth.py

    from fastapi import Depends, HTTPException, status
    from fastapi.security import OAuth2PasswordBearer
    from clerk_sdk import Clerk
    import os

    clerk = Clerk(secret_key=os.environ.get("CLERK_SECRET_KEY"))
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # tokenUrl is not used but required

    async def get_current_user_claims(token: str = Depends(oauth2_scheme)) -> dict:
        try:
            payload = clerk.verify_token(token)
            return payload
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    ```

*   **Step 1.4: Protect API Endpoints**
    *   **Location:** `backend/main.py`
    *   Import the new dependency and apply it to the relevant endpoints. Modify the `/uploadfile/` endpoint to link the job to the user.

    ```python
    # In backend/main.py

    # ... imports
    from . import auth, crud, models, schemas
    from .database import get_db

    # ... (app setup)

    @app.post("/uploadfile/", response_model=schemas.TranslationJob)
    async def create_upload_file(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        api_key: str = Form(...),
        model_name: str = Form("gemini-2.5-flash-lite"),
        style_data: str = Form(None),
        segment_size: int = Form(15000),
        db: Session = Depends(get_db),
        # --- Add this dependency ---
        claims: dict = Depends(auth.get_current_user_claims)
    ):
        # --- Get user from DB using clerk_user_id from claims ---
        clerk_user_id = claims.get("sub")
        db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)
        if not db_user:
            # This case should ideally not happen if webhooks are working correctly
            raise HTTPException(status_code=404, detail="User not found in our database. Please re-login.")
        
        # --- Modify job creation to include owner_id ---
        job_create = schemas.TranslationJobCreate(filename=file.filename, owner_id=db_user.id)
        db_job = crud.create_translation_job(db, job_create)
        
        # ... (rest of the function remains the same)
        return db_job
    ```
    *   **Action:** We will also need to create the `get_user_by_clerk_id` and other user-related functions in `backend/crud.py`.

---

### **Part 2: Database & Webhook Synchronization**

**Objective:** Keep our `User` table synchronized with Clerk's user data.

*   **Step 2.1: Create a Webhook Endpoint**
    *   **Location:** `backend/main.py` (or a new `backend/webhooks.py` for better organization).
    *   Create a new router to handle incoming webhooks from Clerk.

    ```python
    # In backend/main.py (or a new dedicated webhook file)
    from svix import Webhook
    from fastapi import Request, Header

    # Get the secret from an environment variable
    WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")

    @app.post("/api/v1/webhooks/clerk")
    async def handle_clerk_webhook(request: Request, svix_id: str = Header(None), svix_timestamp: str = Header(None), svix_signature: str = Header(None), db: Session = Depends(get_db)):
        if not WEBHOOK_SECRET:
            raise HTTPException(status_code=500, detail="Webhook secret is not configured.")
        
        headers = {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        }
        
        try:
            payload = await request.json()
            wh = Webhook(WEBHOOK_SECRET)
            evt = wh.verify(str(await request.body()), headers)
        except Exception:
            raise HTTPException(status_code=400, detail="Error verifying webhook signature.")

        event_type = evt["type"]
        data = evt["data"]

        if event_type == "user.created":
            crud.create_user(db, schemas.UserCreate(
                clerk_user_id=data["id"],
                email=data["email_addresses"][0]["email_address"],
                name=f'{data.get("first_name", "")} {data.get("last_name", "")}'.strip()
            ))
        elif event_type == "user.updated":
            crud.update_user(db, clerk_id=data["id"], user_update=schemas.UserUpdate(...)) # Populate with updated data
        elif event_type == "user.deleted":
            crud.delete_user(db, clerk_id=data["id"])
            
        return {"status": "success"}
    ```
    *   **Action:** Create corresponding `create_user`, `update_user`, `delete_user` functions in `backend/crud.py` and `schemas.py`.

*   **Step 2.2: Configure Webhook in Clerk Dashboard**
    *   Go to the Clerk Dashboard -> Webhooks.
    *   Create a new endpoint pointing to your deployed backend: `https://<your-railway-app-url>/api/v1/webhooks/clerk`.
    *   Subscribe to `user.created`, `user.updated`, and `user.deleted` events.
    *   Copy the **Signing Secret** and add it as `CLERK_WEBHOOK_SECRET` in your backend environment.

---

### **Part 3: Frontend Integration (Next.js)**

**Objective:** Implement user sign-in, sign-up, and authenticated API calls.

*   **Step 3.1: Environment & Libraries**
    *   Install `@clerk/nextjs`: `npm install @clerk/nextjs` (in the `frontend/` directory).
    *   Add `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` to `frontend/.env.local`.

*   **Step 3.2: Clerk Provider Integration**
    *   **Location:** `frontend/src/app/layout.tsx`
    *   Wrap the root layout with `<ClerkProvider>`.

    ```tsx
    // In frontend/src/app/layout.tsx
    import { ClerkProvider } from '@clerk/nextjs'

    export default function RootLayout({ children }: { children: React.ReactNode }) {
      return (
        <ClerkProvider>
          <html lang="en">
            <body>{children}</body>
          </html>
        </ClerkProvider>
      )
    }
    ```

*   **Step 3.3: Create Authentication Pages & Components**
    *   Create sign-in/sign-up pages using Clerk's file-based routing convention:
        *   `frontend/src/app/(auth)/sign-in/[[...sign-in]]/page.tsx`
        *   `frontend/src/app/(auth)/sign-up/[[...sign-up]]/page.tsx`
    *   Add the `<UserButton>` component to your main navigation/header to show user status.

*   **Step 3.4: Protect Client-Side Routes with Middleware**
    *   **Location:** Create a new file `frontend/middleware.ts`.
    *   This will protect all routes by default, except for public ones.

    ```typescript
    // In frontend/middleware.ts
    import { authMiddleware } from "@clerk/nextjs";

    export default authMiddleware({
      // Add public routes here, e.g., landing page
      publicRoutes: ["/"], 
    });

    export const config = {
      matcher: ["/((?!.+.[\w]+$|_next).*)", "/", "/(api|trpc)(.*)"],
    };
    ```

*   **Step 3.5: Secure API Calls to Backend**
    *   When making `fetch` requests to your FastAPI backend, use `auth().getToken()` from `@clerk/nextjs/server` (for Server Components) or `useAuth().getToken()` (for Client Components) to get the JWT.
    *   Attach the token to the `Authorization` header: `Authorization: Bearer <TOKEN>`. This should be implemented in the frontend code that handles file uploads and other API interactions.
