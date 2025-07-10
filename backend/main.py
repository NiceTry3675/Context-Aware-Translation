import shutil
import os
import traceback
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

# Import database, models, schemas, crud
from . import models, schemas, crud
from .database import engine, SessionLocal

# Import core logic
from core.config_loader import load_config
from core.gemini_model import GeminiModel
from core.dynamic_config_builder import DynamicConfigBuilder
from core.translation_job import TranslationJob
from core.translation_engine import TranslationEngine

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
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_translation_in_background(job_id: int, file_path: str, filename: str, api_key: str):
    """
    This function contains the long-running translation logic
    and will be executed in the background.
    It updates the job status in the database.
    """
    db = SessionLocal() # Get a new session for the background task
    try:
        crud.update_job_status(db, job_id, "PROCESSING")
        print(f"--- [BACKGROUND] Starting translation for Job ID: {job_id}, File: {filename} ---")
        
        # --- 현재: 사용자 제공 API 키 사용 ---
        config = load_config() # .env에서 API 키 외의 다른 설정들을 불러옴
        gemini_api = GeminiModel(
            api_key=api_key, # 프론트엔드로부터 직접 받은 키
            model_name=config['gemini_model_name'],
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config']
        )
        # ------------------------------------

        # --- 이전 방식: 서버 제공 API 키 사용 시 (현재 비활성화) ---
        # config = load_config() # .env에서 모든 설정을 불러옴
        # gemini_api = GeminiModel(
        #     api_key=config['gemini_api_key'],
        #     model_name=config['gemini_model_name'],
        #     safety_settings=config['safety_settings'],
        #     generation_config=config['generation_config']
        # )
        # -----------------------------------------------------
        
        translation_job = TranslationJob(file_path)
        novel_name = translation_job.base_filename
        dyn_config_builder = DynamicConfigBuilder(gemini_api, novel_name)
        engine = TranslationEngine(gemini_api, dyn_config_builder)
        engine.translate_job(translation_job)
        crud.update_job_status(db, job_id, "COMPLETED")
        print(f"--- [BACKGROUND] Translation finished for Job ID: {job_id}, File: {filename} ---")
    except Exception as e:
        crud.update_job_status(db, job_id, "FAILED")
        print(f"--- [BACKGROUND] An unexpected error occurred during translation for Job ID: {job_id}, File: {filename} ---")
        traceback.print_exc()
    finally:
        db.close()

@app.get("/")
def read_root():
    return {"message": "Translation Service Backend is running!"}

@app.post("/uploadfile/", response_model=schemas.TranslationJob)
async def create_upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Form(...),
    db: Session = Depends(get_db)
):
    file_path = f"uploads/{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    job_create = schemas.TranslationJobCreate(filename=file.filename)
    db_job = crud.create_translation_job(db, job_create)
    
    # 백그라운드 작업에 api_key를 전달합니다.
    background_tasks.add_task(run_translation_in_background, db_job.id, file_path, file.filename, api_key)
    
    return db_job

@app.get("/status/{job_id}", response_model=schemas.TranslationJob)
def get_job_status(
    job_id: int,
    db: Session = Depends(get_db)
):
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job

@app.get("/download/{job_id}")
def download_translated_file(job_id: int, db: Session = Depends(get_db)):
    """
    Downloads the translated file for a completed job.
    """
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if db_job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Translation is not completed yet.")

    base, ext = os.path.splitext(db_job.filename)
    translated_filename = f"{base}_translated.txt"
    file_path = os.path.join("translated_novel", translated_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Translated file not found.")

    return FileResponse(path=file_path, filename=translated_filename, media_type='text/plain')