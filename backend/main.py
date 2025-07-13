import shutil
import os
import traceback
import re
import json
import asyncio
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Depends, HTTPException, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from pydantic import BaseModel

# Import database, models, schemas, crud
from . import models, schemas, crud
from .database import engine, SessionLocal

# Import core logic
from core.config.loader import load_config
from core.translation.models.gemini import GeminiModel
from core.config.builder import DynamicConfigBuilder
from core.translation.job import TranslationJob
from core.translation.engine import TranslationEngine
from core.utils.file_parser import parse_document
from core.prompts.manager import PromptManager

# --- Environment Variables ---
# A simple secret key for admin operations.
# In a real production environment, use a more secure method like OAuth2.
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "dev-secret-key")


# Create the database tables
models.Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

# CORS 설정
origins = [
    "http://localhost:3000",  # Next.js 개발 서버
    "https://context-aware-translation.vercel.app", # Vercel 배포 주소
    "https://context-aware-translation-git-main-cat-rans.vercel.app" # Vercel 프리뷰 주소
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Background Translation Task ---
def run_translation_in_background(job_id: int, file_path: str, filename: str, api_key: str, model_name: str, style_data: str = None):
    db = SessionLocal()
    try:
        crud.update_job_status(db, job_id, "PROCESSING")
        print(f"--- [BACKGROUND] Starting translation for Job ID: {job_id}, File: {filename}, Model: {model_name} ---")
        
        config = load_config() 
        gemini_api = GeminiModel(
            api_key=api_key,
            model_name=model_name,
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config'],
            enable_soft_retry=config.get('enable_soft_retry', True)
        )
        translation_job = TranslationJob(file_path)
        
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

# --- SSE Announcement Stream ---
async def announcement_generator(request: Request, db: Session):
    last_sent_id = -1
    while True:
        if await request.is_disconnected():
            print("Client disconnected from announcement stream.")
            break
        
        announcement = crud.get_active_announcement(db)
        if announcement and announcement.id != last_sent_id:
            response_data = schemas.Announcement.from_orm(announcement)
            yield f"data: {response_data.json()}\n\n"
            last_sent_id = announcement.id
        
        await asyncio.sleep(10) # Check for new announcements every 10 seconds

@app.get("/api/v1/announcements/stream")
async def stream_announcements(request: Request, db: Session = Depends(get_db)):
    return StreamingResponse(announcement_generator(request, db), media_type="text/event-stream; charset=utf-8")

# --- Admin Endpoints ---
def verify_admin_secret(x_admin_secret: str = Header(...)):
    if x_admin_secret != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin secret key")

@app.post("/api/v1/admin/announcements", response_model=schemas.Announcement, dependencies=[Depends(verify_admin_secret)])
def create_new_announcement(announcement: schemas.AnnouncementCreate, db: Session = Depends(get_db)):
    return crud.create_announcement(db=db, announcement=announcement)

@app.put("/api/v1/admin/announcements/{announcement_id}/deactivate", response_model=schemas.Announcement, dependencies=[Depends(verify_admin_secret)])
def deactivate_existing_announcement(announcement_id: int, db: Session = Depends(get_db)):
    db_announcement = crud.deactivate_announcement(db, announcement_id)
    if db_announcement is None:
        raise HTTPException(status_code=404, detail="Announcement not found")
    return db_announcement

# --- Main API Endpoints ---
class StyleAnalysisResponse(BaseModel):
    protagonist_name: str
    narration_style_endings: str
    tone_keywords: str
    stylistic_rule: str

@app.post("/api/v1/analyze-style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-1.5-flash"),
):
    if not GeminiModel.validate_api_key(api_key, model_name=model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")

    temp_dir = "uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"temp_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {e}")

    try:
        initial_text = " ".join(parse_document(temp_file_path).split('\n\n')[:5])
        if not initial_text:
            raise HTTPException(status_code=400, detail="Could not extract text from the file.")

        config = load_config()
        gemini_api = GeminiModel(api_key=api_key, model_name=model_name, safety_settings=config['safety_settings'], generation_config=config['generation_config'])
        
        print("\n--- Defining Core Narrative Style via API... ---")
        prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=initial_text)
        style_report_text = gemini_api.generate_text(prompt)
        print(f"Style defined as: {style_report_text}")

        # Parsing logic remains the same...
        parsed_style = {}
        key_mapping = {
            "Protagonist Name": "protagonist_name",
            "Narration Style & Endings (서술 문체 및 어미)": "narration_style_endings",
            "Narration Style & Endings": "narration_style_endings",
            "Core Tone & Keywords (전체 분위기)": "tone_keywords",
            "Core Tone & Keywords": "tone_keywords",
            "Key Stylistic Rule (The \"Golden Rule\"):": "stylistic_rule",
            "Key Stylistic Rule": "stylistic_rule",
        }
        for key_pattern, json_key in key_mapping.items():
            pattern = re.escape(key_pattern) + r":\s*(.*?)(?=\s*\d\.\s*\*|$)"
            match = re.search(pattern, style_report_text, re.DOTALL | re.IGNORECASE)
            if match:
                value = match.group(1).strip().replace('**', '')
                parsed_style[json_key] = value
        
        if len(parsed_style) < 3:
            raise HTTPException(status_code=500, detail=f"Failed to parse all style attributes from the report. Received: '{style_report_text}'")

        return StyleAnalysisResponse(**parsed_style)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred during style analysis: {e}")
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.get("/")
def read_root():
    return {"message": "Translation Service Backend is running!"}

@app.post("/uploadfile/", response_model=schemas.TranslationJob)
async def create_upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-1.5-flash"),
    style_data: str = Form(None),
    db: Session = Depends(get_db)
):
    if not GeminiModel.validate_api_key(api_key, model_name=model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")

    file_path = f"uploads/{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    job_create = schemas.TranslationJobCreate(filename=file.filename)
    db_job = crud.create_translation_job(db, job_create)
    
    background_tasks.add_task(run_translation_in_background, db_job.id, file_path, file.filename, api_key, model_name, style_data)
    
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
    if db_job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Translation is not completed yet.")

    base, ext = os.path.splitext(db_job.filename)
    translated_filename = f"{base}_translated{ext}" if ext == '.epub' else f"{base}_translated.txt"
    media_type = 'application/epub+zip' if ext == '.epub' else 'text/plain'
    file_path = os.path.join("translated_novel", translated_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Translated file not found.")

    return FileResponse(path=file_path, filename=translated_filename, media_type=media_type)

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