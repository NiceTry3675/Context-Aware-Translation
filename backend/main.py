import shutil
from fastapi import FastAPI, File, UploadFile, BackgroundTasks, Depends, HTTPException
import os
import traceback
from sqlalchemy.orm import Session
from typing import Annotated

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

def run_translation_in_background(job_id: int, file_path: str, filename: str):
    """
    This function contains the long-running translation logic
    and will be executed in the background.
    It updates the job status in the database.
    """
    db = SessionLocal() # Get a new session for the background task
    try:
        # Update job status to PROCESSING
        crud.update_job_status(db, job_id, "PROCESSING")
        print(f"--- [BACKGROUND] Starting translation for Job ID: {job_id}, File: {filename} ---")

        # 1. Load base configurations
        config = load_config()

        # 2. Initialize the shared GeminiModel
        gemini_api = GeminiModel(
            api_key=config['gemini_api_key'],
            model_name=config['gemini_model_name'],
            safety_settings=config['safety_settings'],
            generation_config=config['generation_config']
        )
        
        # 3. Create a new translation job from the uploaded file path
        translation_job = TranslationJob(file_path)

        # 4. Initialize the main dynamic config builder and the translation engine
        novel_name = translation_job.base_filename
        dyn_config_builder = DynamicConfigBuilder(gemini_api, novel_name)
        engine = TranslationEngine(gemini_api, dyn_config_builder)

        # 5. Start the translation engine with the job
        engine.translate_job(translation_job)
        
        # Update job status to COMPLETED
        crud.update_job_status(db, job_id, "COMPLETED")
        print(f"--- [BACKGROUND] Translation finished for Job ID: {job_id}, File: {filename} ---")

    except Exception as e:
        # Update job status to FAILED if an error occurs
        crud.update_job_status(db, job_id, "FAILED")
        print(f"--- [BACKGROUND] An unexpected error occurred during translation for Job ID: {job_id}, File: {filename} ---")
        traceback.print_exc()
    finally:
        db.close() # Close the session

@app.get("/")
def read_root():
    return {"message": "Translation Service Backend is running!"}

@app.post("/uploadfile/", response_model=schemas.TranslationJob)
async def create_upload_file(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    db: Session = Depends(get_db) # Inject database session
):
    """
    Receives a file, saves it, creates a job record, and starts the translation process in the background.
    """
    # Define the path to save the uploaded file
    file_path = f"uploads/{file.filename}"

    # Save the uploaded file
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {e}")

    # Create a new job record in the database
    job_create = schemas.TranslationJobCreate(filename=file.filename)
    db_job = crud.create_translation_job(db, job_create)

    # Add the long-running translation task to the background
    background_tasks.add_task(run_translation_in_background, db_job.id, file_path, file.filename)

    return db_job # Return the newly created job object

@app.get("/status/{job_id}", response_model=schemas.TranslationJob)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """
    Retrieves the status of a specific translation job.
    """
    db_job = crud.get_job(db, job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job
