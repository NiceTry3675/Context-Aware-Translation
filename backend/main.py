# --- 1. Standard Library Imports ---
import shutil
import os
import traceback
import re
import json
import asyncio
import gc
import uuid

# --- 2. Third-party Library Imports ---
from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Depends, HTTPException, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from svix import Webhook

# --- Load Environment Variables FIRST ---
load_dotenv() # This loads variables from the .env file at the project root

# --- 3. Internal/Local Application Imports ---
from . import models, schemas, crud, auth
from .database import engine, SessionLocal
from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.translation.models.openrouter import OpenRouterModel
from core.config.builder import DynamicConfigBuilder
from core.translation.job import TranslationJob
from core.translation.engine import TranslationEngine
from core.utils.file_parser import parse_document
from core.prompts.manager import PromptManager

# --- Environment Variables & Constants ---
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev-secret-key")
CLERK_WEBHOOK_SECRET = os.environ.get("CLERK_WEBHOOK_SECRET")

# --- Database Initialization ---
# Create all database tables based on the models
models.Base.metadata.create_all(bind=engine)

# --- FastAPI App Initialization ---
app = FastAPI()

# --- Middleware Configuration ---
origins = [
    "http://localhost:3000",  # Next.js development server
    "https://context-aware-translation.vercel.app", # Vercel production deployment
    "https://context-aware-translation-git-main-cat-rans.vercel.app", # Vercel main branch preview
    "https://context-aware-translation-git-dev-cat-rans.vercel.app" # Vercel dev branch preview
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Dependency Injection ---
def get_db():
    """Dependency to get a database session for a single request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Helper Functions ---
def get_model_api(api_key: str, model_name: str, config: dict):
    """Factory function to get the correct model API instance."""
    if api_key.startswith("sk-or-"):
        print(f"--- [API] Using OpenRouter model: {model_name} ---")
        return OpenRouterModel(
            api_key=api_key,
            model_name=model_name,
            enable_soft_retry=config.get('enable_soft_retry', True)
        )
    else:
        print(f"--- [API] Using Gemini model: {model_name} ---")
        return GeminiModel(
            api_key=api_key,
            model_name=model_name,
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config'],
            enable_soft_retry=config.get('enable_soft_retry', True)
        )

def validate_api_key(api_key: str, model_name: str):
    """Validates the API key based on its prefix."""
    if api_key.startswith("sk-or-"):
        return OpenRouterModel.validate_api_key(api_key, model_name)
    else:
        return GeminiModel.validate_api_key(api_key, model_name)

# --- Background Task Definition ---
def run_translation_in_background(job_id: int, file_path: str, filename: str, api_key: str, model_name: str, style_data: str = None, segment_size: int = 15000):
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "PROCESSING")
        print(f"--- [BACKGROUND] Starting translation for Job ID: {job_id}, File: {filename}, Model: {model_name} ---")
        
        config = load_config()
        gemini_api = get_model_api(api_key, model_name, config)

        translation_job = TranslationJob(
            file_path, 
            original_filename=filename, 
            target_segment_size=segment_size
        )
        
        initial_core_style_text = None
        protagonist_name = "protagonist"
        if style_data:
            try:
                style_dict = json.loads(style_data)
                print(f"--- [BACKGROUND] Using user-defined core style for Job ID: {job_id}: {style_dict} ---")
                protagonist_name = style_dict.get('protagonist_name', 'protagonist')
                style_parts = [
                    f"1. **Protagonist Name:** {protagonist_name}",
                    f"2. **Narration Style & Endings (서술 문체 및 어미):** {style_dict.get('narration_style_endings', 'Not specified')}",
                    f"3. **Core Tone & Keywords (전체 분위기):** {style_dict.get('tone_keywords', 'Not specified')}",
                    f"4. **Key Stylistic Rule (The \"Golden Rule\"):** {style_dict.get('stylistic_rule', 'Not specified')}"
                ]
                initial_core_style_text = "\n".join(style_parts)
            except json.JSONDecodeError:
                print(f"--- [BACKGROUND] WARNING: Could not decode style_data JSON for Job ID: {job_id}. Proceeding with auto-analysis. ---")

        dyn_config_builder = DynamicConfigBuilder(gemini_api, protagonist_name)
        engine = TranslationEngine(gemini_api, dyn_config_builder, db=db, job_id=job_id, initial_core_style=initial_core_style_text)
        
        engine.translate_job(translation_job)
        crud.update_job_status(db, job_id, "COMPLETED")
        print(f"--- [BACKGROUND] Translation finished for Job ID: {job_id}, File: {filename} ---")
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}"
        crud.update_job_status(db, job_id, "FAILED", error_message=error_message)
        print(f"--- [BACKGROUND] {error_message} for Job ID: {job_id}, File: {filename} ---")
        traceback.print_exc()
    finally:
        db.close()
        gc.collect()
        print(f"--- [BACKGROUND] Job ID: {job_id} finished. DB session closed and GC collected. ---")

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Translation Service Backend is running!"}

# --- Translation Endpoints ---

class StyleAnalysisResponse(BaseModel):
    protagonist_name: str
    narration_style_endings: str
    tone_keywords: str
    stylistic_rule: str

@app.post("/api/v1/analyze-style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite-preview-06-17"),
    # No longer requires user authentication for this specific endpoint
):
    if not validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")

    temp_dir = "uploads"
    os.makedirs(temp_dir, exist_ok=True)
    # Create a unique temporary filename to avoid collisions
    unique_id = uuid.uuid4()
    temp_file_path = os.path.join(temp_dir, f"temp_{unique_id}_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {e}")

    try:
        try:
            text_segments = parse_document(temp_file_path)
        except Exception as parse_error:
            raise HTTPException(status_code=400, detail=f"Failed to parse the uploaded file: {str(parse_error)}")
            
        if not text_segments:
            raise HTTPException(status_code=400, detail="Could not extract text from the file.")
        
        initial_text = " ".join(text_segments.split('\n\n')[:5])

        config = load_config()
        model_api = get_model_api(api_key, model_name, config)
        
        print("\n--- Defining Core Narrative Style via API... ---")
        prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=initial_text)
        style_report_text = model_api.generate_text(prompt)
        print(f"Style defined as: {style_report_text}")

        parsed_style = {}
        key_mapping = {
            "Protagonist Name": "protagonist_name",
            "Protagonist Name (주인공 이름)": "protagonist_name",
            "Narration Style & Endings (서술 문체 및 어미)": "narration_style_endings",
            "Narration Style & Endings": "narration_style_endings",
            "Core Tone & Keywords (전체 분위기)": "tone_keywords",
            "Core Tone & Keywords": "tone_keywords",
            "Key Stylistic Rule (The \"Golden Rule\")": "stylistic_rule",
            "Key Stylistic Rule": "stylistic_rule",
        }

        for key_pattern, json_key in key_mapping.items():
            pattern = re.escape(key_pattern) + r":\s*(.*?)(?=\s*\d\.\s*|$)"
            match = re.search(pattern, style_report_text, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip().replace('**', '')
                parsed_style[json_key] = value
        
        if len(parsed_style) < 3:
            found_keys = list(parsed_style.keys())
            error_detail = (
                "Failed to parse all style attributes from the report. "
                f"Successfully parsed: {found_keys}. "
                f"Received from AI: '{style_report_text}'"
            )
            raise HTTPException(status_code=500, detail=error_detail)

        return StyleAnalysisResponse(**parsed_style)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred during style analysis: {e}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.post("/uploadfile/", response_model=schemas.TranslationJob)
async def create_upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite-preview-06-17"),
    style_data: str = Form(None),
    segment_size: int = Form(15000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_required_user)
):
    if not validate_api_key(api_key, model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")

    job_create = schemas.TranslationJobCreate(filename=file.filename, owner_id=current_user.id)
    db_job = crud.create_translation_job(db, job_create)
    
    sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    unique_filename = f"{db_job.id}_{sanitized_filename}"
    file_path = f"uploads/{unique_filename}"
    
    os.makedirs("uploads", exist_ok=True)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        crud.update_job_status(db, db_job.id, "FAILED", error_message=f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    crud.update_job_filepath(db, job_id=db_job.id, filepath=file_path)

    background_tasks.add_task(run_translation_in_background, db_job.id, file_path, file.filename, api_key, model_name, style_data, segment_size)
    
    return db_job

@app.get("/status/{job_id}", response_model=schemas.TranslationJob)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

@app.get("/download/{job_id}")
def download_translated_file(job_id: int, db: Session = Depends(get_db)):
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if db_job.status not in ["COMPLETED", "FAILED"]:
        raise HTTPException(status_code=400, detail=f"Translation is not completed yet. Current status: {db_job.status}")
    if not db_job.filepath:
        raise HTTPException(status_code=404, detail="Filepath not found for this job.")

    unique_base = os.path.splitext(os.path.basename(db_job.filepath))[0]
    original_filename_base, original_ext = os.path.splitext(db_job.filename)

    if original_ext.lower() == '.epub':
        output_ext = '.epub'
        media_type = 'application/epub+zip'
    else:
        output_ext = '.txt'
        media_type = 'text/plain'

    translated_unique_filename = f"{unique_base}_translated{output_ext}"
    file_path = os.path.join("translated_novel", translated_unique_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Translated file not found at path: {file_path}")

    user_translated_filename = f"{original_filename_base}_translated{output_ext}"

    return FileResponse(path=file_path, filename=user_translated_filename, media_type=media_type)

@app.get("/download/logs/{job_id}/{log_type}")
def download_log_file(job_id: int, log_type: str, db: Session = Depends(get_db)):
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if log_type not in ["prompts", "context"]:
        raise HTTPException(status_code=400, detail="Invalid log type. Must be 'prompts' or 'context'.")

    base, _ = os.path.splitext(db_job.filename)
    log_dir = "debug_prompts" if log_type == "prompts" else "context_log"
    log_filename = f"{log_type}_job_{job_id}_{base}.txt"
    log_path = os.path.join(log_dir, log_filename)

    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail=f"{log_type.capitalize()} log file not found.")

    return FileResponse(path=log_path, filename=log_filename, media_type="text/plain")

# --- Webhook Endpoints ---

@app.post("/api/v1/webhooks/clerk")
async def handle_clerk_webhook(request: Request, svix_id: str = Header(None), svix_timestamp: str = Header(None), svix_signature: str = Header(None), db: Session = Depends(get_db)):
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
        email_address = data.get("email_addresses", [{}])[0].get("email_address")

        user_in = schemas.UserCreate(
            clerk_user_id=data["id"],
            email=email_address or None, # Ensure None if empty
            name=user_name or None
        )
        crud.create_user(db, user=user_in)
    elif event_type == "user.updated":
        clerk_user_id = data["id"]
        db_user = crud.get_user_by_clerk_id(db, clerk_id=clerk_user_id)
        
        user_name = f'{data.get("first_name", "")} {data.get("last_name", "")}'.strip()
        email_address = data.get("email_addresses", [{}])[0].get("email_address")

        if db_user:
            user_update = schemas.UserUpdate(email=email_address or None, name=user_name or None)
            crud.update_user(db, clerk_id=clerk_user_id, user_update=user_update)
        else:
            print(f"--- [INFO] Webhook received user.updated for non-existent user {clerk_user_id}. Creating them now. ---")
            user_in = schemas.UserCreate(
                clerk_user_id=clerk_user_id,
                email=email_address or None, # Ensure None if empty
                name=user_name or None
            )
            crud.create_user(db, user=user_in)
    elif event_type == "user.deleted":
        crud.delete_user(db, clerk_id=data["id"])
        
    return {"status": "success"}

# --- SSE Announcement Stream Endpoint ---

async def announcement_generator(request: Request):
    last_sent_announcement = None
    client_id = id(request)
    print(f"📡 새 클라이언트 연결: {client_id}")

    def get_announcement_from_db():
        with SessionLocal() as db:
            return crud.get_active_announcement(db)

    try:
        current_announcement = get_announcement_from_db()
        if current_announcement:
            announcement_data = {
                "id": current_announcement.id,
                "message": current_announcement.message,
                "is_active": current_announcement.is_active,
                "created_at": current_announcement.created_at.isoformat()
            }
            json_str = json.dumps(announcement_data, ensure_ascii=False)
            yield f"data: {json_str}\n\n"
            last_sent_announcement = current_announcement
            print(f"📤 초기 공지 전송 (클라이언트 {client_id}): ID {current_announcement.id}")
    except Exception as e:
        print(f"❌ 초기 공지 전송 오류: {e}")

    while True:
        if await request.is_disconnected():
            print(f"🔌 클라이언트 연결 해제: {client_id}")
            break

        try:
            current_announcement = get_announcement_from_db()
            
            should_send = False
            announcement_data = {}

            if current_announcement is None and last_sent_announcement is not None:
                announcement_data = {
                    "id": last_sent_announcement.id,
                    "message": last_sent_announcement.message,
                    "is_active": False,
                    "created_at": last_sent_announcement.created_at.isoformat()
                }
                should_send = True
                last_sent_announcement = None
                print(f"🔇 공지 비활성화 전송 (클라이언트 {client_id})")

            elif current_announcement is not None:
                if (last_sent_announcement is None or
                    current_announcement.id != last_sent_announcement.id or
                    current_announcement.message != last_sent_announcement.message or
                    current_announcement.is_active != last_sent_announcement.is_active):
                    
                    announcement_data = {
                        "id": current_announcement.id,
                        "message": current_announcement.message,
                        "is_active": current_announcement.is_active,
                        "created_at": current_announcement.created_at.isoformat()
                    }
                    should_send = True
                    last_sent_announcement = current_announcement
                    print(f"📢 새 공지/변경 전송 (클라이언트 {client_id}): ID {current_announcement.id}")

            if should_send:
                json_str = json.dumps(announcement_data, ensure_ascii=False)
                yield f"data: {json_str}\n\n"

        except Exception as e:
            print(f"❌ SSE 스트림 오류 (클라이언트 {client_id}): {e}")
        
        await asyncio.sleep(120)

@app.get("/api/v1/announcements/stream")
async def stream_announcements(request: Request):
    return StreamingResponse(announcement_generator(request), media_type="text/event-stream; charset=utf-8")

# --- Admin Endpoints ---

def verify_admin_secret(x_admin_secret: str = Header(...)):
    if x_admin_secret != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin secret key")

@app.post("/api/v1/admin/announcements", dependencies=[Depends(verify_admin_secret)])
def create_new_announcement(announcement: schemas.AnnouncementCreate, db: Session = Depends(get_db)):
    result = crud.create_announcement(db=db, announcement=announcement)
    return JSONResponse(
        content={
            "id": result.id,
            "message": result.message,
            "is_active": result.is_active,
            "created_at": result.created_at.isoformat()
        },
        media_type="application/json; charset=utf-8"
    )

@app.put("/api/v1/admin/announcements/{announcement_id}/deactivate", dependencies=[Depends(verify_admin_secret)])
def deactivate_existing_announcement(announcement_id: int, db: Session = Depends(get_db)):
    db_announcement = crud.deactivate_announcement(db, announcement_id)
    if db_announcement is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return JSONResponse(
        content={
            "id": db_announcement.id,
            "message": db_announcement.message,
            "is_active": db_announcement.is_active,
            "created_at": db_announcement.created_at.isoformat()
        },
        media_type="application/json; charset=utf-8"
    )

@app.put("/api/v1/admin/announcements/deactivate-all", dependencies=[Depends(verify_admin_secret)])
def deactivate_all_announcements(db: Session = Depends(get_db)):
    """모든 활성 공지를 비활성화합니다."""
    updated_count = crud.deactivate_all_announcements(db)
    return JSONResponse(
        content={
            "message": f"모든 공지가 비활성화되었습니다.",
            "deactivated_count": updated_count,
            "success": True
        },
        media_type="application/json; charset=utf-8"
    )

