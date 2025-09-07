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
from typing import Tuple, Optional, Any, Dict

from backend.config.settings import get_settings


class FileManager:
    """Centralized file management utilities for backend services."""
    
    def __init__(self):
        """Initialize file manager with settings-based configuration."""
        # Use settings for directory paths
        settings = get_settings()
        
        # Temporary directory for uploads without job ID
        self.TEMP_DIR = settings.temp_directory or "/tmp/translation_temp"
        
        # Community images directory (separate from job files)
        self.COMMUNITY_IMAGE_DIR = "community/images"
        
        # Job-centric base directory for all job-related files
        self.JOB_STORAGE_BASE = settings.job_storage_base or "logs/jobs"
    
    def save_uploaded_file(self, file: Any, filename: str) -> Tuple[str, str]:
        """
        Save an uploaded file temporarily (for analysis without job ID).
        
        Args:
            file: File object to save (with file attribute)
            filename: Original filename
            
        Returns:
            Tuple of (file_path, unique_id)
        """
        os.makedirs(self.TEMP_DIR, exist_ok=True)
        
        unique_id = str(uuid.uuid4())
        temp_file_path = os.path.join(self.TEMP_DIR, f"temp_{unique_id}_{filename}")
        
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
        # Use job-centric directory structure
        job_dir = os.path.join(self.JOB_STORAGE_BASE, str(job_id), "input")
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
        os.makedirs(self.COMMUNITY_IMAGE_DIR, exist_ok=True)
        
        unique_id = str(uuid.uuid4())
        file_extension = os.path.splitext(filename)[1]
        unique_filename = f"{unique_id}{file_extension}"
        file_path = os.path.join(self.COMMUNITY_IMAGE_DIR, unique_filename)
        
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
        original_filename_base, original_ext = os.path.splitext(job.filename)
        
        # Use .txt for translated files regardless of original format
        translated_filename = "translated.txt"
        user_translated_filename = f"{original_filename_base}_translated.txt"
        
        # Set media type
        media_type = "text/plain"
        
        # Use job-centric directory structure
        file_path = os.path.join(self.JOB_STORAGE_BASE, str(job.id), "output", translated_filename)
        return file_path, user_translated_filename, media_type
    
    def get_validation_report_path(self, job) -> str:
        """
        Get the validation report file path for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Validation report file path
        """
        # Use job-centric directory structure
        report_filename = "validation_report.json"
        report_path = os.path.join(self.JOB_STORAGE_BASE, str(job.id), "validation", report_filename)
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        return report_path
    
    def get_post_edit_log_path(self, job) -> str:
        """
        Get the post-edit log file path for a job.
        
        Args:
            job: Translation job instance
            
        Returns:
            Post-edit log file path
        """
        # Use job-centric directory structure
        log_filename = "postedit_log.json"
        log_path = os.path.join(self.JOB_STORAGE_BASE, str(job.id), "postedit", log_filename)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        return log_path
    
    def delete_job_files(self, job) -> None:
        """
        Delete all files associated with a translation job.
        
        Args:
            job: Translation job instance
        """
        # Delete entire job directory
        job_dir = os.path.join(self.JOB_STORAGE_BASE, str(job.id))
        if os.path.exists(job_dir):
            shutil.rmtree(job_dir)
    
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
        return bool(filepath and os.path.exists(filepath))
    
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
    
    def get_job_prompt_log_path(self, job_id: int) -> str:
        """
        Get the debug prompt log file path for a job.
        
        Args:
            job_id: Translation job ID
            
        Returns:
            Debug prompt log file path
        """
        log_path = os.path.join(self.JOB_STORAGE_BASE, str(job_id), "prompts", "debug_prompts.json")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        return log_path
    
    def get_job_context_log_path(self, job_id: int) -> str:
        """
        Get the context log file path for a job.
        
        Args:
            job_id: Translation job ID
            
        Returns:
            Context log file path
        """
        log_path = os.path.join(self.JOB_STORAGE_BASE, str(job_id), "context", "context_log.json")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        return log_path
    
    def get_job_illustration_path(self, job_id: int) -> str:
        """
        Get the illustrations file path for a job.
        
        Args:
            job_id: Translation job ID
            
        Returns:
            Illustrations file path
        """
        file_path = os.path.join(self.JOB_STORAGE_BASE, str(job_id), "illustrations", "illustrations.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        return file_path
    
    def get_job_character_prompts_path(self, job_id: int) -> str:
        """
        Get the character base prompts file path for a job.
        
        Args:
            job_id: Translation job ID
            
        Returns:
            Character base prompts file path
        """
        file_path = os.path.join(self.JOB_STORAGE_BASE, str(job_id), "illustrations", "character_base_prompts.json")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        return file_path
    
    def get_job_directory(self, job_id: int) -> str:
        """
        Get the base directory for a job.
        
        Args:
            job_id: Translation job ID
            
        Returns:
            Job base directory path
        """
        job_dir = os.path.join(self.JOB_STORAGE_BASE, str(job_id))
        os.makedirs(job_dir, exist_ok=True)
        return job_dir
    
    def cleanup_temp_files(self, temp_dir: Optional[str] = None) -> None:
        """
        Clean up temporary files in the specified directory.
        
        Args:
            temp_dir: Directory to clean. Defaults to TEMP_DIR.
        """
        if temp_dir is None:
            temp_dir = self.TEMP_DIR
            
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
    
    def migrate_job_files_to_new_structure(self, job_id: int) -> Dict[str, str]:
        """
        Migrate existing job files from legacy structure to new job-centric structure.
        
        Args:
            job_id: Translation job ID
            
        Returns:
            Dictionary of migrated file paths (old -> new)
        """
        migrated_files = {}
        job_dir = os.path.join(self.JOB_STORAGE_BASE, str(job_id))
        
        # List of file patterns to migrate with their new locations
        migration_map = [
            # Input files
            (f"uploads/{job_id}_*", os.path.join(job_dir, "input")),
            (f"uploads/{job_id}/*", os.path.join(job_dir, "input")),
            
            # Output files
            (f"translated_novel/*_{job_id}_*.txt", os.path.join(job_dir, "output")),
            (f"translated_novel/{job_id}/*.txt", os.path.join(job_dir, "output")),
            
            # Validation reports
            (f"logs/validation_logs/*job_{job_id}_*.json", os.path.join(job_dir, "validation")),
            (f"translated_novel/{job_id}_*validation_report.json", os.path.join(job_dir, "validation")),
            
            # Post-edit logs
            (f"logs/postedit_logs/*job_{job_id}_*.json", os.path.join(job_dir, "postedit")),
            (f"translated_novel/{job_id}_*postedit_log.json", os.path.join(job_dir, "postedit")),
            
            # Debug prompts
            (f"logs/debug_prompts/*job_{job_id}_*.txt", os.path.join(job_dir, "prompts")),
            (f"logs/debug_prompts/*job_{job_id}_*.json", os.path.join(job_dir, "prompts")),
            
            # Context logs
            (f"logs/context_log/*job_{job_id}_*.txt", os.path.join(job_dir, "context")),
            (f"logs/context_logs/*job_{job_id}_*.json", os.path.join(job_dir, "context")),
            
            # Illustrations
            (f"translated_novel/{job_id}/illustrations.json", os.path.join(job_dir, "illustrations")),
            (f"translated_novel/{job_id}/character_base_prompts.json", os.path.join(job_dir, "illustrations")),
        ]
        
        # Perform migration
        import glob
        for pattern, target_dir in migration_map:
            for old_path in glob.glob(pattern):
                if os.path.exists(old_path):
                    # Create target directory if needed
                    os.makedirs(target_dir, exist_ok=True)
                    
                    # Determine new filename
                    basename = os.path.basename(old_path)
                    # Simplify filename for new structure
                    if "validation_report" in basename:
                        new_name = "validation_report.json"
                    elif "postedit_log" in basename:
                        new_name = "postedit_log.json"
                    elif "debug_prompts" in basename or "_prompts" in basename:
                        new_name = "debug_prompts.json" if basename.endswith(".json") else "debug_prompts.txt"
                    elif "context_log" in basename or "_context" in basename:
                        new_name = "context_log.json" if basename.endswith(".json") else "context_log.txt"
                    elif "translated" in basename:
                        new_name = "translated.txt"
                    else:
                        new_name = basename
                    
                    new_path = os.path.join(target_dir, new_name)
                    
                    # Move file
                    try:
                        shutil.move(old_path, new_path)
                        migrated_files[old_path] = new_path
                        print(f"Migrated: {old_path} -> {new_path}")
                    except Exception as e:
                        print(f"Failed to migrate {old_path}: {e}")
        
        return migrated_files
    
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