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
    "https://context-aware-translation-git-main-cat-rans.vercel.app" # Vercel 프리뷰 주소
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
        
        # 사용자가 정의한 스타일 처리
        initial_core_style_text = None
        protagonist_name = "protagonist" # 기본값
        if style_data:
            try:
                style_dict = json.loads(style_data)
                print(f"--- [BACKGROUND] Using user-defined core style for Job ID: {job_id}: {style_dict} ---")
                
                # 주인공 이름 설정
                protagonist_name = style_dict.get('protagonist_name', 'protagonist')

                # JSON을 core 로직이 기대하는 텍스트 형식으로 변환 (마크다운 포함)
                style_parts = [
                    f"1. **Protagonist Name:** {protagonist_name}",
                    f"2. **Narration Style & Endings (서술 문체 및 어미):** {style_dict.get('narration_style_endings', 'Not specified')}",
                    f"3. **Core Tone & Keywords (전체 분위기):** {style_dict.get('tone_keywords', 'Not specified')}",
                    f"4. **Key Stylistic Rule (The \"Golden Rule\"):** {style_dict.get('stylistic_rule', 'Not specified')}"
                ]
                initial_core_style_text = "\n".join(style_parts)

            except json.JSONDecodeError:
                print(f"--- [BACKGROUND] WARNING: Could not decode style_data JSON for Job ID: {job_id}. Proceeding with auto-analysis. ---")

        # DynamicConfigBuilder를 주인공 이름과 함께 생성
        dyn_config_builder = DynamicConfigBuilder(gemini_api, protagonist_name)

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
    protagonist_name: str
    narration_style_endings: str
    tone_keywords: str
    stylistic_rule: str

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

        print("\n--- Defining Core Narrative Style via API... ---")
        prompt = PromptManager.DEFINE_NARRATIVE_STYLE.format(sample_text=initial_text)
        style_report_text = gemini_api.generate_text(prompt)
        print(f"Style defined as: {style_report_text}")

        # 5. 텍스트 결과를 JSON으로 파싱 (새로운 안정적인 로직)
        parsed_style = {}
        key_mapping = {
            "Protagonist Name": "protagonist_name",
            "Narration Style & Endings (서술 문체 및 어미)": "narration_style_endings",
            "Narration Style & Endings": "narration_style_endings",
            "Core Tone & Keywords (전체 분위기)": "tone_keywords",
            "Core Tone & Keywords": "tone_keywords",
            "Key Stylistic Rule (The \"Golden Rule\")": "stylistic_rule",
            "Key Stylistic Rule": "stylistic_rule",
        }

        # 정규식을 사용하여 각 항목을 추출
        for key_pattern, json_key in key_mapping.items():
            # 정규식 패턴 생성 (키와 그 뒤에 오는 내용을 non-greedy하게 매칭)
            # Lookahead (?=...)를 사용하여 다음 항목의 시작 전까지 모든 내용을 캡처
            pattern = re.escape(key_pattern) + r":\s*(.*?)(?=\s*\d\.\s*\*|$)"
            match = re.search(pattern, style_report_text, re.DOTALL | re.IGNORECASE)
            if match:
                # 값에서 앞뒤 공백과 마크다운을 정리
                value = match.group(1).strip().replace('**', '')
                parsed_style[json_key] = value
        
        # 중복 키를 처리했으므로, 유니크한 값만 남김
        # (예: "Core Tone & Keywords (3-5 words)"와 "Core Tone & Keywords"가 둘 다 tone_keywords에 매핑됨)
        # 실제로는 정규식 탐색 순서에 따라 하나만 매칭될 가능성이 높음.

        if len(parsed_style) < 3:
            # 파싱 실패 시, 더 유용한 디버깅을 위해 정규식으로 찾은 부분이라도 보여주자.
            found_keys = list(parsed_style.keys())
            error_detail = (
                "Failed to parse all style attributes from the report. "
                f"Successfully parsed: {found_keys}. "
                f"Received the following text from the AI, which could not be fully parsed: '{style_report_text}'"
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

@app.get("/download/logs/{job_id}/{log_type}")
def download_log_file(job_id: int, log_type: str, db: Session = Depends(get_db)):
    """
    Downloads the specified log file (prompts or context) for a given job.
    """
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    if log_type not in ["prompts", "context"]:
        raise HTTPException(status_code=400, detail="Invalid log type specified. Must be 'prompts' or 'context'.")

    base, _ = os.path.splitext(db_job.filename)
    log_dir = "debug_prompts" if log_type == "prompts" else "context_log"
    log_filename = f"{log_type}_job_{job_id}_{base}.txt"
    log_path = os.path.join(log_dir, log_filename)

    if not os.path.exists(log_path):
        raise HTTPException(status_code=404, detail=f"{log_type.capitalize()} log file not found.")

    return FileResponse(path=log_path, filename=log_filename, media_type="text/plain")
