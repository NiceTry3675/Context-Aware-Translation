import shutil
import os
import traceback
import re
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Depends, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Dict
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
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_translation_in_background(job_id: int, file_path: str, filename: str, api_key: str, model_name: str, style_data: str = None):
    """
    This function contains the long-running translation logic
    and will be executed in the background.
    It updates the job status in the database.
    """
    db = SessionLocal() # Get a new session for the background task
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
# --- 이전 방식: 서버 제공 API 키 사용 시 (현재 비활성화) ---
# config = load_config()  # .env에서 모든 설정을 불러옴
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

        # 만약 사용자가 정의한 스타일이 있다면, 여기서 텍스트 형식으로 재구성
        initial_core_style_text = None
        if style_data:
            try:
                style_dict = json.loads(style_data)
                print(f"--- [BACKGROUND] Using user-defined core style for Job ID: {job_id}: {style_dict} ---")
                
                # JSON을 core 로직이 기대하는 텍스트 형식으로 변환 (마크다운 포함)
                style_parts = [
                    f"1. **Narrative Perspective:** {style_dict.get('narrative_perspective', 'Not specified')}",
                    f"2. **Primary Speech Level:** {style_dict.get('primary_speech_level', 'Not specified')}",
                    f"3. **Tone (Written/Spoken):** {style_dict.get('tone', 'Not specified')}"
                ]
                initial_core_style_text = "\n".join(style_parts)

            except json.JSONDecodeError:
                print(f"--- [BACKGROUND] WARNING: Could not decode style_data JSON for Job ID: {job_id}. Proceeding with auto-analysis. ---")

        # TranslationEngine 생성 시 재구성된 텍스트 스타일 전달
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

# Pydantic model for the style analysis response
class StyleAnalysisResponse(BaseModel):
    narrative_perspective: str
    primary_speech_level: str
    tone: str

@app.post("/api/v1/analyze-style", response_model=StyleAnalysisResponse)
async def analyze_style(
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite-preview-06-17"),
):
    # 1. API 키 유효성 검사
    if not GeminiModel.validate_api_key(api_key, model_name=model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")

    # 2. 파일을 임시로 저장
    temp_dir = "uploads"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, f"temp_{file.filename}")
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save temporary file: {e}")

    try:
        # 3. 저장된 파일의 경로를 사용하여 텍스트 파싱
        text_segments = parse_document(temp_file_path)
        if not text_segments:
            raise HTTPException(status_code=400, detail="Could not extract text from the file.")
        # Join segments to get a single block of text for analysis
        initial_text = " ".join(text_segments.split('\n\n')[:5]) # Split by paragraphs and take first 5

        # 4. 스타일 분석 로직 실행
        config = load_config()
        gemini_api = GeminiModel(
            api_key=api_key,
            model_name=model_name,
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config'],
            enable_soft_retry=config.get('enable_soft_retry', True)
        )

        # --- TranslationEngine._define_core_style 로직을 직접 구현 ---
        print("\n--- Defining Core Narrative Style via API... ---")
        prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=initial_text)
        style_report_text = gemini_api.generate_text(prompt)
        print(f"Style defined as: {style_report_text}")
        # ----------------------------------------------------------

        # 5. 텍스트 결과를 JSON으로 파싱 (개선된 로직)
        parsed_style = {}
        key_mapping = {
            'Narrative Perspective': 'narrative_perspective',
            'Primary Speech Level': 'primary_speech_level',
            'Tone (Written/Spoken)': 'tone',
            'Tone': 'tone'
        }

        # AI 응답을 숫자(1., 2., 3.)를 기준으로 분리
        segments = re.split(r'\s*\d\.\s*', style_report_text)
        
        for segment in segments:
            if ':' not in segment:
                continue

            # 첫 번째 콜론을 기준으로 키와 값으로 분리
            key_raw, value_full = segment.split(':', 1)
            
            # 키 정리: 양쪽의 ** 와 공백 제거
            key = key_raw.replace('**', '').strip()
            
            # 값 정리: 
            # 1. 부가 설명(" - ")이 있다면 그 앞부분만 사용
            # 2. 양쪽의 ** 와 공백을 추가로 제거
            value = value_full.split(' - ')[0].replace('**', '').strip()

            if key in key_mapping:
                json_key = key_mapping[key]
                parsed_style[json_key] = value

        if len(parsed_style) < 3:
            error_detail = (
                "Failed to parse all style attributes from the report. "
                f"Received the following text from the AI, which could not be parsed: '{style_report_text}'"
            )
            raise HTTPException(status_code=500, detail=error_detail)

        return StyleAnalysisResponse(**parsed_style)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An error occurred during style analysis: {e}")

    finally:
        # 6. 임시 파일 삭제
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


@app.get("/")
def read_root():
    return {"message": "Translation Service Backend is running!"}

import json

@app.post("/uploadfile/", response_model=schemas.TranslationJob)
async def create_upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    api_key: str = Form(...),
    model_name: str = Form("gemini-2.5-flash-lite-preview-06-17"),
    style_data: str = Form(None), # 사용자 정의 스타일 (JSON 문자열)
    db: Session = Depends(get_db)
):
    # 1. API 키 유효성 검사 먼저 수행
    if not GeminiModel.validate_api_key(api_key, model_name=model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model. Please check your key and selected model.")

    # 2. 유효한 키일 경우에만 파일 저장 및 작업 생성 진행
    file_path = f"uploads/{file.filename}"
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    job_create = schemas.TranslationJobCreate(filename=file.filename)
    db_job = crud.create_translation_job(db, job_create)
    
    # 3. 백그라운드 작업에 api_key, model_name, style_data 전달
    background_tasks.add_task(run_translation_in_background, db_job.id, file_path, file.filename, api_key, model_name, style_data)
    
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
    Downloads the translated file for a completed job, handling different file types.
    """
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if db_job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Translation is not completed yet.")

    # Determine the output filename and media type based on the original file's extension
    base, ext = os.path.splitext(db_job.filename)
    
    if ext.lower() == '.epub':
        translated_filename = f"{base}_translated.epub"
        media_type = 'application/epub+zip'
    else:
        translated_filename = f"{base}_translated.txt"
        media_type = 'text/plain'
        
    file_path = os.path.join("translated_novel", translated_filename)

    if not os.path.exists(file_path):
        # Fallback for cases where the output might be a .txt even if input was epub
        # This can happen if the epub translation logic changes.
        fallback_filename = f"{base}_translated.txt"
        fallback_path = os.path.join("translated_novel", fallback_filename)
        if os.path.exists(fallback_path):
            file_path = fallback_path
            translated_filename = fallback_filename
            media_type = 'text/plain'
        else:
            raise HTTPException(status_code=404, detail="Translated file not found.")

    return FileResponse(path=file_path, filename=translated_filename, media_type=media_type)
