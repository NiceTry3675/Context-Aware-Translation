"""
File Manager

Centralized file operations and path handling for backend services.
Eliminates duplicate file handling logic across all services.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Tuple, Optional
from backend import models


class FileManager:
    """Centralized file management utilities for backend services."""
    
    # Directory constants
    UPLOAD_DIR = "uploads"
    TRANSLATED_DIR = "translated_novel"
    VALIDATION_LOG_DIR = "logs/validation_logs"
    POST_EDIT_LOG_DIR = "logs/postedit_logs"
    IMAGE_UPLOAD_DIR = "uploads/images"
    
    @staticmethod
    def save_uploaded_file(file, filename: str) -> Tuple[str, str]:
        """
        Save an uploaded file and return the path and unique filename.
        
        Args:
            file: File object to save
            filename: Original filename
            
        Returns:
            Tuple of (file_path, unique_id)
        """
        os.makedirs(FileManager.UPLOAD_DIR, exist_ok=True)
        
        unique_id = uuid.uuid4()
        temp_file_path = os.path.join(FileManager.UPLOAD_DIR, f"temp_{unique_id}_{filename}")
        
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return temp_file_path, str(unique_id)
    
    @staticmethod
    def save_community_image(file, filename: str) -> str:
        """
        Save a community image file and return the file path.
        
        Args:
            file: Image file to save
            filename: Original filename
            
        Returns:
            Saved file path
        """
        os.makedirs(FileManager.IMAGE_UPLOAD_DIR, exist_ok=True)
        
        unique_id = uuid.uuid4()
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{unique_id}{file_extension}"
        file_path = os.path.join(FileManager.IMAGE_UPLOAD_DIR, unique_filename)
        
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return file_path
    
    @staticmethod
    def get_translated_file_path(job: models.TranslationJob) -> Tuple[str, str, str]:
        """
        Get the translated file path and media type for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Tuple of (file_path, user_filename, media_type)
        """
        unique_base = os.path.splitext(os.path.basename(job.filepath))[0]
        original_filename_base, original_ext = os.path.splitext(job.filename)
        
        # Use .txt for translated files regardless of original format
        translated_unique_filename = f"{unique_base}_translated.txt"
        user_translated_filename = f"{original_filename_base}_translated.txt"
        
        # Set media type
        media_type = "text/plain"
        
        file_path = os.path.join(FileManager.TRANSLATED_DIR, translated_unique_filename)
        
        return file_path, user_translated_filename, media_type
    
    @staticmethod
    def get_validation_report_path(job: models.TranslationJob) -> str:
        """
        Get the validation report file path for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Validation report file path
        """
        os.makedirs(FileManager.VALIDATION_LOG_DIR, exist_ok=True)
        report_filename = f"{job.id}_{os.path.splitext(job.filename)[0]}_validation_report.json"
        return os.path.join(FileManager.VALIDATION_LOG_DIR, report_filename)
    
    @staticmethod
    def get_post_edit_log_path(job: models.TranslationJob) -> str:
        """
        Get the post-edit log file path for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Post-edit log file path
        """
        os.makedirs(FileManager.POST_EDIT_LOG_DIR, exist_ok=True)
        log_filename = f"{job.id}_{os.path.splitext(job.filename)[0]}_postedit_log.json"
        return os.path.join(FileManager.POST_EDIT_LOG_DIR, log_filename)
    
    @staticmethod
    def delete_job_files(job: models.TranslationJob) -> None:
        """
        Delete all files associated with a translation job.
        
        Args:
            job: Translation job instance
        """
        # Delete uploaded file
        if job.filepath and os.path.exists(job.filepath):
            os.remove(job.filepath)
        
        # Delete translated file
        translated_path, _, _ = FileManager.get_translated_file_path(job)
        if os.path.exists(translated_path):
            os.remove(translated_path)
        
        # Delete validation report if exists
        if hasattr(job, 'validation_report_path') and job.validation_report_path:
            if os.path.exists(job.validation_report_path):
                os.remove(job.validation_report_path)
        
        # Delete post-edit log if exists  
        if hasattr(job, 'post_edit_log_path') and job.post_edit_log_path:
            if os.path.exists(job.post_edit_log_path):
                os.remove(job.post_edit_log_path)
    
    @staticmethod
    def ensure_directory_exists(directory_path: str) -> None:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path: Path to directory
        """
        os.makedirs(directory_path, exist_ok=True)
    
    @staticmethod
    def get_unique_filename_base(filepath: str) -> str:
        """
        Get the unique filename base from a file path.
        
        Args:
            filepath: Full file path
            
        Returns:
            Unique filename base without extension
        """
        return os.path.splitext(os.path.basename(filepath))[0]
    
    @staticmethod
    def get_filename_stem(filepath: str) -> str:
        """
        Get the filename stem for display purposes.
        
        Args:
            filepath: Full file path
            
        Returns:
            Formatted filename stem
        """
        return Path(filepath).stem.replace('_', ' ').title()
    
    @staticmethod
    def file_exists(filepath: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filepath: File path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return filepath and os.path.exists(filepath)
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """
        Get file extension from filename.
        
        Args:
            filename: Filename to extract extension from
            
        Returns:
            File extension including dot (e.g., '.txt')
        """
        return os.path.splitext(filename)[1]
    
    @staticmethod
    def cleanup_temp_files(temp_dir: str = None) -> None:
        """
        Clean up temporary files in the specified directory.
        
        Args:
            temp_dir: Directory to clean. Defaults to UPLOAD_DIR.
        """
        if temp_dir is None:
            temp_dir = FileManager.UPLOAD_DIR
            
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if filename.startswith("temp_"):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Warning: Could not remove temp file {file_path}: {e}")