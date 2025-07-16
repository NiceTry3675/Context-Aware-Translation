import shutil
import os
import traceback
import re
import json
import asyncio
import gc
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Depends, HTTPException, Form, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
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
    "https://context-aware-translation-git-main-cat-rans.vercel.app", # Vercel 프리뷰 주소
    "https://context-aware-translation-git-dev-cat-rans.vercel.app"
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
        # Check if we need to resume the job
        db_job = crud.get_job(db, job_id)
        is_resume = db_job.last_successful_segment > 0
        initial_context = json.loads(db_job.context_snapshot_json) if is_resume else {}

        crud.update_job_status(db, job_id, "PROCESSING")
        print(f"--- [BACKGROUND] Starting translation for Job ID: {job_id}, File: {filename}, Model: {model_name} ---")
        if is_resume:
            print(f"--- Resuming from segment: {db_job.last_successful_segment + 1}")

        config = load_config()
        gemini_api = GeminiModel(
            api_key=api_key,
            model_name=model_name,
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config'],
            enable_soft_retry=config.get('enable_soft_retry', True)
        )
        
        translation_job = TranslationJob(file_path, original_filename=filename, is_resume=is_resume)
        
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
        engine = TranslationEngine(
            gemini_api, 
            dyn_config_builder, 
            db=db, 
            job_id=job_id, 
            initial_core_style=initial_core_style_text,
            resume_from_segment=db_job.last_successful_segment,
            initial_context=initial_context
        )
        
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
        # Explicitly run garbage collection to free up memory
        gc.collect()
        print(f"--- [BACKGROUND] Job ID: {job_id} finished. DB session closed and GC collected. ---")

# --- SSE Announcement Stream ---
async def announcement_generator(request: Request):
    last_sent_announcement = None
    client_id = id(request)
    print(f"📡 새 클라이언트 연결: {client_id}")

    # DB 세션을 with 문으로 관리하여 자동 반환 보장
    def get_announcement_from_db():
        with SessionLocal() as db:
            return crud.get_active_announcement(db)

    try:
        # 초기 연결 시 즉시 현재 활성 공지 전송
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
            # 오류 발생 시에도 루프를 계속 진행할 수 있도록 break를 제거하거나,
            # 혹은 특정 오류에 대해서만 break를 수행하도록 처리할 수 있습니다.
            # 여기서는 일단 연결을 유지하도록 break를 주석 처리합니다.
            # break 
        
        await asyncio.sleep(120)

@app.get("/api/v1/announcements/stream")
async def stream_announcements(request: Request):
    # 더 이상 `db` 의존성을 직접 주입하지 않음
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
    model_name: str = Form("gemini-2.5-flash-lite-preview-06-17"),
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
        # 저장된 파일의 경로를 사용하여 텍스트 파싱
        try:
            text_segments = parse_document(temp_file_path)
        except Exception as parse_error:
            raise HTTPException(status_code=400, detail=f"Failed to parse the uploaded file: {str(parse_error)}")
            
        if not text_segments:
            raise HTTPException(status_code=400, detail="Could not extract text from the file.")
        # Join segments to get a single block of text for analysis
        initial_text = " ".join(text_segments.split('\n\n')[:5]) # Split by paragraphs and take first 5

        # 스타일 분석 로직 실행
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

        # 텍스트 결과를 JSON으로 파싱 (안정적인 로직)
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
        # 임시 파일 삭제
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
    model_name: str = Form("gemini-2.5-flash-lite-preview-06-17"),
    style_data: str = Form(None),
    db: Session = Depends(get_db)
):
    if not GeminiModel.validate_api_key(api_key, model_name=model_name):
        raise HTTPException(status_code=400, detail="Invalid API Key or unsupported model.")

    # 1. Create DB job first to get a unique job_id
    job_create = schemas.TranslationJobCreate(filename=file.filename)
    db_job = crud.create_translation_job(db, job_create)
    
    # 2. Sanitize filename and create a unique filename using the job_id
    # This prevents overwriting files with the same name.
    sanitized_filename = re.sub(r'[^a-zA-Z0-9_.-]', '_', file.filename)
    unique_filename = f"{db_job.id}_{sanitized_filename}"
    file_path = f"uploads/{unique_filename}"
    
    os.makedirs("uploads", exist_ok=True)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        # If file saving fails, we should ideally roll back the DB job creation
        # or mark it as failed. For now, we'll raise an exception.
        crud.update_job_status(db, db_job.id, "FAILED", error_message=f"Failed to save file: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # 3. Update the job record with the unique file path
    crud.update_job_filepath(db, job_id=db_job.id, filepath=file_path)

    # 4. Add the background task with the correct unique file path and original filename
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
    if db_job.status not in ["COMPLETED", "FAILED"]:
        raise HTTPException(status_code=400, detail=f"Translation is not completed yet. Current status: {db_job.status}")
    if not db_job.filepath:
        raise HTTPException(status_code=404, detail="Filepath not found for this job.")

    # Construct the unique path to the translated file
    unique_base = os.path.splitext(os.path.basename(db_job.filepath))[0]
    original_filename_base, original_ext = os.path.splitext(db_job.filename)

    # If the original file is an EPUB, the translated file should also be an EPUB.
    # Otherwise, the output is always a .txt file.
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

    # For the user, provide a clean filename with the correct extension
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