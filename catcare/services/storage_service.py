"""
Storage service for file upload/download operations
"""

import os
import uuid
from typing import Optional
from werkzeug.utils import secure_filename
from flask import current_app

# Google Cloud Storage disabled for local development
GCS_AVAILABLE = False


class StorageService:
    """Service class for file storage operations"""

    def __init__(self):
        # Force local storage since Google Cloud free trial ended
        self.is_cloud = False  # Always use local storage
        self.bucket_name = os.getenv('STORAGE_BUCKET', 'local-uploads')  # Keep for reference

    def upload_file(self, file, folder: str = "") -> Optional[str]:
        """Upload a file and return its URL"""
        if not file or not file.filename:
            return None

        try:
            filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"

            if self.is_cloud:
                return self._upload_to_gcs(file, folder, filename)
            else:
                return self._upload_to_local(file, folder, filename)

        except Exception as e:
            current_app.logger.error(f"Error uploading file: {e}")
            return None

    def delete_file(self, file_url: str) -> bool:
        """Delete a file by its URL"""
        try:
            if self.is_cloud and "storage.googleapis.com" in file_url:
                return self._delete_from_gcs(file_url)
            else:
                return self._delete_from_local(file_url)
        except Exception as e:
            current_app.logger.error(f"Error deleting file: {e}")
            return False

    def _upload_to_gcs(self, file, folder: str, filename: str) -> str:
        """Upload file to Google Cloud Storage"""
        # Since we're running locally only, always fall back to local storage
        current_app.logger.info("GCS disabled for local development, using local storage")
        return self._upload_to_local(file, folder, filename)

    def _upload_to_local(self, file, folder: str, filename: str) -> str:
        """Upload file to local filesystem"""
        upload_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        return f"/uploads/{folder}/{filename}" if folder else f"/uploads/{filename}"

    def _delete_from_gcs(self, file_url: str) -> bool:
        """Delete file from Google Cloud Storage"""
        # Since we're running locally only, skip GCS deletion
        current_app.logger.info("GCS disabled for local development, skipping cloud deletion")
        return True  # Return True to avoid errors

    def _delete_from_local(self, file_url: str) -> bool:
        """Delete file from local filesystem"""
        try:
            # Extract relative path from URL
            relative_path = file_url.replace("/uploads/", "")
            filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], relative_path)

            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            return False
        except Exception:
            return False
