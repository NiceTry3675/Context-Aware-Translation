"""
File Manager

Centralized file operations and path handling for backend services.
Eliminates duplicate file handling logic across all services.

Refactored from backend/services/utils/file_manager.py
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Tuple, Optional, Any

from backend.config.settings import get_settings


class FileManager:
    """Centralized file management utilities for backend services."""
    
    def __init__(self):
        """Initialize file manager with settings-based configuration."""
        # Use settings for directory paths
        settings = get_settings()
        self.UPLOAD_DIR = settings.upload_directory or "uploads"
        self.TRANSLATED_DIR = "translated_novel"
        self.VALIDATION_LOG_DIR = "logs/validation_logs"
        self.POST_EDIT_LOG_DIR = "logs/postedit_logs"
        self.IMAGE_UPLOAD_DIR = os.path.join(self.UPLOAD_DIR, "images")
    
    def save_uploaded_file(self, file: Any, filename: str) -> Tuple[str, str]:
        """
        Save an uploaded file and return the path and unique filename.
        
        Args:
            file: File object to save (with file attribute)
            filename: Original filename
            
        Returns:
            Tuple of (file_path, unique_id)
        """
        os.makedirs(self.UPLOAD_DIR, exist_ok=True)
        
        unique_id = str(uuid.uuid4())
        temp_file_path = os.path.join(self.UPLOAD_DIR, f"temp_{unique_id}_{filename}")
        
        with open(temp_file_path, "wb") as buffer:
            # Handle different file object types
            if hasattr(file, 'file'):
                shutil.copyfileobj(file.file, buffer)
            else:
                shutil.copyfileobj(file, buffer)
            
        return temp_file_path, unique_id
    
    def save_job_file(self, file: Any, job_id: int, filename: str) -> str:
        """
        Save a file for a specific job.
        
        Args:
            file: File object to save
            job_id: Translation job ID
            filename: Original filename
            
        Returns:
            Saved file path
        """
        job_dir = os.path.join(self.UPLOAD_DIR, str(job_id))
        os.makedirs(job_dir, exist_ok=True)
        
        file_path = os.path.join(job_dir, filename)
        
        with open(file_path, "wb") as buffer:
            if hasattr(file, 'file'):
                shutil.copyfileobj(file.file, buffer)
            else:
                shutil.copyfileobj(file, buffer)
        
        return file_path
    
    def save_community_image(self, file: Any, filename: str) -> str:
        """
        Save a community image file and return the file path.
        
        Args:
            file: Image file to save
            filename: Original filename
            
        Returns:
            Saved file path
        """
        os.makedirs(self.IMAGE_UPLOAD_DIR, exist_ok=True)
        
        unique_id = str(uuid.uuid4())
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{unique_id}{file_extension}"
        file_path = os.path.join(self.IMAGE_UPLOAD_DIR, unique_filename)
        
        with open(file_path, "wb") as buffer:
            if hasattr(file, 'file'):
                shutil.copyfileobj(file.file, buffer)
            else:
                shutil.copyfileobj(file, buffer)
            
        return file_path
    
    def get_translated_file_path(self, job) -> Tuple[str, str, str]:
        """
        Get the translated file path and media type for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Tuple of (file_path, user_filename, media_type)
        """
        # Extract the unique base from the job's filepath
        unique_base = os.path.splitext(os.path.basename(job.filepath))[0]
        original_filename_base, original_ext = os.path.splitext(job.filename)
        
        # Use .txt for translated files regardless of original format
        translated_unique_filename = f"{unique_base}_translated.txt"
        user_translated_filename = f"{original_filename_base}_translated.txt"
        
        # Set media type
        media_type = "text/plain"
        
        # Look in the TRANSLATED_DIR, not UPLOAD_DIR
        file_path = os.path.join(self.TRANSLATED_DIR, translated_unique_filename)
        
        return file_path, user_translated_filename, media_type
    
    def get_validation_report_path(self, job) -> str:
        """
        Get the validation report file path for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Validation report file path
        """
        # Use job-specific directory
        job_dir = os.path.join(self.UPLOAD_DIR, str(job.id))
        os.makedirs(job_dir, exist_ok=True)
        
        return os.path.join(job_dir, "validation_report.json")
    
    def get_post_edit_log_path(self, job) -> str:
        """
        Get the post-edit log file path for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Post-edit log file path
        """
        # Check if log exists in job directory
        job_dir = os.path.join(self.UPLOAD_DIR, str(job.id), "logs")
        os.makedirs(job_dir, exist_ok=True)
        
        return os.path.join(job_dir, "postedit_log.json")
    
    def delete_job_files(self, job) -> None:
        """
        Delete all files associated with a translation job.
        
        Args:
            job: Translation job instance
        """
        # Delete entire job directory
        job_dir = os.path.join(self.UPLOAD_DIR, str(job.id))
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
        
        # Clean up legacy locations if they exist
        if job.filepath and os.path.exists(job.filepath):
            try:
                os.remove(job.filepath)
            except:
                pass
        
        # Delete translated file in legacy location
        translated_path = os.path.join(self.TRANSLATED_DIR, f"{self.get_unique_filename_base(job.filepath)}_translated.txt")
        if os.path.exists(translated_path):
            try:
                os.remove(translated_path)
            except:
                pass
    
    def ensure_directory_exists(self, directory_path: str) -> None:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            directory_path: Path to directory
        """
        os.makedirs(directory_path, exist_ok=True)
    
    def get_unique_filename_base(self, filepath: str) -> str:
        """
        Get the unique filename base from a file path.
        
        Args:
            filepath: Full file path
            
        Returns:
            Unique filename base without extension
        """
        return os.path.splitext(os.path.basename(filepath))[0]
    
    def get_filename_stem(self, filepath: str) -> str:
        """
        Get the filename stem for display purposes.
        
        Args:
            filepath: Full file path
            
        Returns:
            Formatted filename stem
        """
        return Path(filepath).stem.replace('_', ' ').title()
    
    def file_exists(self, filepath: str) -> bool:
        """
        Check if a file exists.
        
        Args:
            filepath: File path to check
            
        Returns:
            True if file exists, False otherwise
        """
        return filepath and os.path.exists(filepath)
    
    def get_file_extension(self, filename: str) -> str:
        """
        Get file extension from filename.
        
        Args:
            filename: Filename to extract extension from
            
        Returns:
            File extension including dot (e.g., '.txt')
        """
        return os.path.splitext(filename)[1]
    
    def get_file_size(self, filepath: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            filepath: File path
            
        Returns:
            File size in bytes, or 0 if file doesn't exist
        """
        if self.file_exists(filepath):
            return os.path.getsize(filepath)
        return 0
    
    def cleanup_temp_files(self, temp_dir: Optional[str] = None) -> None:
        """
        Clean up temporary files in the specified directory.
        
        Args:
            temp_dir: Directory to clean. Defaults to UPLOAD_DIR.
        """
        if temp_dir is None:
            temp_dir = self.UPLOAD_DIR
            
        if os.path.exists(temp_dir):
            for filename in os.listdir(temp_dir):
                if filename.startswith("temp_"):
                    file_path = os.path.join(temp_dir, filename)
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Warning: Could not remove temp file {file_path}: {e}")
    
    def read_file(self, filepath: str, encoding: str = 'utf-8') -> str:
        """
        Read file contents.
        
        Args:
            filepath: File path to read
            encoding: File encoding
            
        Returns:
            File contents as string
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not self.file_exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    
    def write_file(self, filepath: str, content: str, encoding: str = 'utf-8') -> None:
        """
        Write content to file.
        
        Args:
            filepath: File path to write to
            content: Content to write
            encoding: File encoding
        """
        self.ensure_directory_exists(os.path.dirname(filepath))
        
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(content)
    
    def copy_file(self, source: str, destination: str) -> None:
        """
        Copy a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
        """
        if not self.file_exists(source):
            raise FileNotFoundError(f"Source file not found: {source}")
        
        self.ensure_directory_exists(os.path.dirname(destination))
        shutil.copy2(source, destination)
    
    def move_file(self, source: str, destination: str) -> None:
        """
        Move a file from source to destination.
        
        Args:
            source: Source file path
            destination: Destination file path
        """
        if not self.file_exists(source):
            raise FileNotFoundError(f"Source file not found: {source}")
        
        self.ensure_directory_exists(os.path.dirname(destination))
        shutil.move(source, destination)