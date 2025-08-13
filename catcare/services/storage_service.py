"""
Storage service for file upload/download operations with advanced media processing support
"""

import os
import uuid
import shutil
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from flask import current_app, send_file, make_response

# Google Cloud Storage disabled for local development
GCS_AVAILABLE = False


class StorageService:
    """Enhanced service class for file storage operations with media processing support"""

    def __init__(self):
        # Force local storage since Google Cloud free trial ended
        self.is_cloud = False  # Always use local storage
        self.bucket_name = os.getenv('STORAGE_BUCKET', 'local-uploads')  # Keep for reference
        self.logger = logging.getLogger(__name__)
        
        # Storage configuration
        self.max_storage_size = int(os.getenv('MAX_STORAGE_SIZE', 10 * 1024 * 1024 * 1024))  # 10GB default
        self.cleanup_threshold = 0.9  # Start cleanup when 90% full
        self.thumbnail_cache_duration = timedelta(days=30)  # Cache thumbnails for 30 days
        
        # Storage paths
        self.original_folder = 'originals'
        self.processed_folder = 'processed'
        self.thumbnail_folder = 'thumbnails'
        self.temp_folder = 'temp'
        
        # Initialize storage directories
        self._ensure_storage_directories()

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
    
    def store_processed_media(self, original_file_path: str, processed_file_path: str, 
                            thumbnails: List[Dict[str, Any]], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Store original, processed, and thumbnail versions of media with metadata.
        
        Args:
            original_file_path: Path to the original file
            processed_file_path: Path to the processed file
            thumbnails: List of thumbnail information dictionaries
            metadata: Media metadata dictionary
            
        Returns:
            Dictionary containing storage information and URLs
            
        Raises:
            IOError: If storage operation fails
        """
        try:
            storage_info = {
                'original_url': None,
                'processed_url': None,
                'thumbnail_urls': {},
                'metadata_stored': False,
                'storage_paths': {}
            }
            
            # Generate unique identifier for this media set
            media_id = str(uuid.uuid4())
            base_filename = os.path.splitext(os.path.basename(original_file_path))[0]
            
            # Validate that at least original file exists
            if not os.path.exists(original_file_path):
                raise IOError(f"Original file not found: {original_file_path}")
            
            # Store original file
            original_filename = f"{media_id}_{base_filename}_original{os.path.splitext(original_file_path)[1]}"
            original_storage_path = self._store_file_in_folder(
                original_file_path, self.original_folder, original_filename
            )
            storage_info['original_url'] = f"/uploads/{self.original_folder}/{original_filename}"
            storage_info['storage_paths']['original'] = original_storage_path
            self.logger.debug(f"Stored original file: {original_storage_path}")
            
            # Store processed file
            if os.path.exists(processed_file_path) and processed_file_path != original_file_path:
                processed_filename = f"{media_id}_{base_filename}_processed{os.path.splitext(processed_file_path)[1]}"
                processed_storage_path = self._store_file_in_folder(
                    processed_file_path, self.processed_folder, processed_filename
                )
                storage_info['processed_url'] = f"/uploads/{self.processed_folder}/{processed_filename}"
                storage_info['storage_paths']['processed'] = processed_storage_path
                self.logger.debug(f"Stored processed file: {processed_storage_path}")
            else:
                # Use original file as processed if no separate processed file
                storage_info['processed_url'] = storage_info['original_url']
                storage_info['storage_paths']['processed'] = storage_info['storage_paths'].get('original')
            
            # Store thumbnails
            thumbnail_storage_info = []
            for thumbnail in thumbnails:
                try:
                    # Convert thumbnail dict to proper format if needed
                    if isinstance(thumbnail, dict):
                        thumbnail_dict = thumbnail
                    else:
                        # Handle ThumbnailInfo object
                        thumbnail_dict = {
                            'size_label': thumbnail.size_label,
                            'filename': thumbnail.filename,
                            'file_size': thumbnail.file_size,
                            'width': thumbnail.width,
                            'height': thumbnail.height
                        }
                    
                    # Construct full path for thumbnail file
                    # Thumbnails are generated in the same directory as the original file
                    original_dir = os.path.dirname(original_file_path)
                    thumbnail_source_path = os.path.join(original_dir, thumbnail_dict['filename'])
                    thumbnail_dict['filename'] = thumbnail_source_path
                    
                    thumbnail_info = self._store_thumbnail(media_id, base_filename, thumbnail_dict)
                    if thumbnail_info:
                        storage_info['thumbnail_urls'][thumbnail_info['size_label']] = thumbnail_info['url']
                        thumbnail_storage_info.append(thumbnail_info)
                        self.logger.debug(f"Stored thumbnail {thumbnail_info['size_label']}: {thumbnail_info['path']}")
                except Exception as e:
                    self.logger.warning(f"Failed to store thumbnail {thumbnail.get('size_label', 'unknown')}: {str(e)}")
            
            storage_info['thumbnails'] = thumbnail_storage_info
            
            # Store metadata (this would typically be stored in database)
            try:
                metadata_path = self._store_metadata(media_id, metadata)
                storage_info['metadata_stored'] = True
                storage_info['storage_paths']['metadata'] = metadata_path
                self.logger.debug(f"Stored metadata: {metadata_path}")
            except Exception as e:
                self.logger.warning(f"Failed to store metadata: {str(e)}")
            
            # Update storage usage statistics
            self._update_storage_stats()
            
            self.logger.info(f"Successfully stored processed media set {media_id}")
            return storage_info
            
        except Exception as e:
            self.logger.error(f"Failed to store processed media: {str(e)}")
            # Cleanup any partially stored files
            self._cleanup_failed_storage(storage_info.get('storage_paths', {}))
            raise IOError(f"Media storage failed: {str(e)}")
    
    def serve_thumbnail(self, thumbnail_filename: str, size_label: str = None) -> Any:
        """Serve thumbnail with proper caching headers.
        
        Args:
            thumbnail_filename: Name of the thumbnail file
            size_label: Size label for additional validation
            
        Returns:
            Flask response with thumbnail and caching headers
            
        Raises:
            FileNotFoundError: If thumbnail not found
        """
        try:
            thumbnail_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], 
                self.thumbnail_folder, 
                thumbnail_filename
            )
            
            if not os.path.exists(thumbnail_path):
                raise FileNotFoundError(f"Thumbnail not found: {thumbnail_filename}")
            
            # Create response with caching headers
            response = make_response(send_file(thumbnail_path))
            
            # Set cache headers for efficient thumbnail serving
            response.headers['Cache-Control'] = 'public, max-age=2592000'  # 30 days
            response.headers['ETag'] = f'"{os.path.getmtime(thumbnail_path)}"'
            
            # Set content type based on file extension
            if thumbnail_filename.lower().endswith('.jpg') or thumbnail_filename.lower().endswith('.jpeg'):
                response.headers['Content-Type'] = 'image/jpeg'
            elif thumbnail_filename.lower().endswith('.png'):
                response.headers['Content-Type'] = 'image/png'
            elif thumbnail_filename.lower().endswith('.webp'):
                response.headers['Content-Type'] = 'image/webp'
            
            self.logger.debug(f"Served thumbnail: {thumbnail_filename}")
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to serve thumbnail {thumbnail_filename}: {str(e)}")
            raise
    
    def cleanup_failed_processing(self, file_paths: List[str]) -> bool:
        """Clean up files from failed processing attempts.
        
        Args:
            file_paths: List of file paths to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            cleanup_count = 0
            for file_path in file_paths:
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        cleanup_count += 1
                        self.logger.debug(f"Cleaned up failed processing file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Could not clean up file {file_path}: {str(e)}")
            
            self.logger.info(f"Cleaned up {cleanup_count} failed processing files")
            return True
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            return False
    
    def get_storage_usage(self) -> Dict[str, Any]:
        """Get current storage usage statistics.
        
        Returns:
            Dictionary containing storage usage information
        """
        try:
            upload_folder = current_app.config["UPLOAD_FOLDER"]
            
            usage_stats = {
                'total_size': 0,
                'original_size': 0,
                'processed_size': 0,
                'thumbnail_size': 0,
                'temp_size': 0,
                'file_counts': {
                    'original': 0,
                    'processed': 0,
                    'thumbnails': 0,
                    'temp': 0
                },
                'usage_percentage': 0,
                'cleanup_needed': False
            }
            
            # Calculate folder sizes
            folder_mappings = [
                (self.original_folder, 'original_size', 'original'),
                (self.processed_folder, 'processed_size', 'processed'),
                (self.thumbnail_folder, 'thumbnail_size', 'thumbnails'),
                (self.temp_folder, 'temp_size', 'temp')
            ]
            
            for folder_name, folder_key, count_key in folder_mappings:
                folder_path = os.path.join(upload_folder, folder_name)
                if os.path.exists(folder_path):
                    folder_size, file_count = self._get_folder_size(folder_path)
                    usage_stats[folder_key] = folder_size
                    usage_stats['file_counts'][count_key] = file_count
                    usage_stats['total_size'] += folder_size
            
            # Calculate usage percentage
            if self.max_storage_size > 0:
                usage_stats['usage_percentage'] = (usage_stats['total_size'] / self.max_storage_size) * 100
                usage_stats['cleanup_needed'] = usage_stats['usage_percentage'] > (self.cleanup_threshold * 100)
            
            return usage_stats
            
        except Exception as e:
            self.logger.error(f"Failed to get storage usage: {str(e)}")
            return {'error': str(e)}
    
    def optimize_storage(self) -> Dict[str, Any]:
        """Optimize storage by cleaning up old temporary files and unused thumbnails.
        
        Returns:
            Dictionary containing optimization results
        """
        try:
            optimization_results = {
                'temp_files_cleaned': 0,
                'old_thumbnails_cleaned': 0,
                'space_freed': 0,
                'errors': []
            }
            
            upload_folder = current_app.config["UPLOAD_FOLDER"]
            
            # Clean up temporary files older than 24 hours
            temp_folder_path = os.path.join(upload_folder, self.temp_folder)
            if os.path.exists(temp_folder_path):
                cutoff_time = datetime.now() - timedelta(hours=24)
                temp_cleaned = self._cleanup_old_files(temp_folder_path, cutoff_time)
                optimization_results['temp_files_cleaned'] = temp_cleaned['files_cleaned']
                optimization_results['space_freed'] += temp_cleaned['space_freed']
            
            # Clean up old thumbnails if storage is getting full
            usage_stats = self.get_storage_usage()
            if usage_stats.get('cleanup_needed', False):
                thumbnail_folder_path = os.path.join(upload_folder, self.thumbnail_folder)
                if os.path.exists(thumbnail_folder_path):
                    cutoff_time = datetime.now() - self.thumbnail_cache_duration
                    thumbnail_cleaned = self._cleanup_old_files(thumbnail_folder_path, cutoff_time)
                    optimization_results['old_thumbnails_cleaned'] = thumbnail_cleaned['files_cleaned']
                    optimization_results['space_freed'] += thumbnail_cleaned['space_freed']
            
            self.logger.info(f"Storage optimization completed: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Storage optimization failed: {str(e)}")
            return {'error': str(e)}

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
    
    def _ensure_storage_directories(self) -> None:
        """Ensure all required storage directories exist."""
        try:
            upload_folder = current_app.config["UPLOAD_FOLDER"]
            
            directories = [
                self.original_folder,
                self.processed_folder,
                self.thumbnail_folder,
                self.temp_folder
            ]
            
            for directory in directories:
                dir_path = os.path.join(upload_folder, directory)
                os.makedirs(dir_path, exist_ok=True)
                self.logger.debug(f"Ensured directory exists: {dir_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to create storage directories: {str(e)}")
            raise
    
    def _store_file_in_folder(self, source_path: str, folder: str, filename: str) -> str:
        """Store a file in a specific folder.
        
        Args:
            source_path: Path to source file
            folder: Target folder name
            filename: Target filename
            
        Returns:
            Path to stored file
            
        Raises:
            IOError: If storage fails
        """
        try:
            target_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], folder)
            target_path = os.path.join(target_dir, filename)
            
            # Copy file to target location
            shutil.copy2(source_path, target_path)
            
            return target_path
            
        except Exception as e:
            self.logger.error(f"Failed to store file {source_path} in {folder}: {str(e)}")
            raise IOError(f"File storage failed: {str(e)}")
    
    def _store_thumbnail(self, media_id: str, base_filename: str, thumbnail: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Store a single thumbnail file.
        
        Args:
            media_id: Unique media identifier
            base_filename: Base filename without extension
            thumbnail: Thumbnail information dictionary
            
        Returns:
            Dictionary with thumbnail storage information or None if failed
        """
        try:
            # Get thumbnail file path from the thumbnail info
            thumbnail_source_path = thumbnail.get('filename')
            
            # Handle both absolute and relative paths
            if thumbnail_source_path and not os.path.isabs(thumbnail_source_path):
                # If it's a relative path, assume it's in the same directory as the original
                # This is a common case when thumbnails are generated in the same directory
                thumbnail_source_path = os.path.abspath(thumbnail_source_path)
            
            if not thumbnail_source_path or not os.path.exists(thumbnail_source_path):
                self.logger.warning(f"Thumbnail source file not found: {thumbnail_source_path}")
                return None
            
            # Generate storage filename
            size_label = thumbnail.get('size_label', 'unknown')
            thumbnail_filename = f"{media_id}_{base_filename}_thumb_{size_label}.jpg"
            
            # Store thumbnail
            thumbnail_storage_path = self._store_file_in_folder(
                thumbnail_source_path, self.thumbnail_folder, thumbnail_filename
            )
            
            return {
                'size_label': size_label,
                'filename': thumbnail_filename,
                'path': thumbnail_storage_path,
                'url': f"/uploads/{self.thumbnail_folder}/{thumbnail_filename}",
                'file_size': thumbnail.get('file_size', 0),
                'width': thumbnail.get('width', 0),
                'height': thumbnail.get('height', 0)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to store thumbnail: {str(e)}")
            return None
    
    def _store_metadata(self, media_id: str, metadata: Dict[str, Any]) -> str:
        """Store metadata as JSON file.
        
        Args:
            media_id: Unique media identifier
            metadata: Metadata dictionary
            
        Returns:
            Path to stored metadata file
            
        Raises:
            IOError: If metadata storage fails
        """
        try:
            import json
            
            metadata_filename = f"{media_id}_metadata.json"
            metadata_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], 'metadata')
            os.makedirs(metadata_dir, exist_ok=True)
            
            metadata_path = os.path.join(metadata_dir, metadata_filename)
            
            # Add storage timestamp
            storage_metadata = metadata.copy()
            storage_metadata['stored_at'] = datetime.now().isoformat()
            storage_metadata['media_id'] = media_id
            
            with open(metadata_path, 'w') as f:
                json.dump(storage_metadata, f, indent=2, default=str)
            
            return metadata_path
            
        except Exception as e:
            self.logger.error(f"Failed to store metadata: {str(e)}")
            raise IOError(f"Metadata storage failed: {str(e)}")
    
    def _cleanup_failed_storage(self, storage_paths: Dict[str, str]) -> None:
        """Clean up files from failed storage operation.
        
        Args:
            storage_paths: Dictionary of storage paths to clean up
        """
        try:
            for path_type, path in storage_paths.items():
                if path and os.path.exists(path):
                    try:
                        os.unlink(path)
                        self.logger.debug(f"Cleaned up failed storage file ({path_type}): {path}")
                    except Exception as e:
                        self.logger.warning(f"Could not clean up {path_type} file {path}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Failed storage cleanup error: {str(e)}")
    
    def _update_storage_stats(self) -> None:
        """Update storage usage statistics."""
        try:
            # This could be enhanced to update database statistics
            # For now, just log current usage
            usage_stats = self.get_storage_usage()
            if usage_stats.get('cleanup_needed', False):
                self.logger.warning(f"Storage usage at {usage_stats['usage_percentage']:.1f}% - cleanup recommended")
            else:
                self.logger.debug(f"Storage usage: {usage_stats['usage_percentage']:.1f}%")
        except Exception as e:
            self.logger.debug(f"Could not update storage stats: {str(e)}")
    
    def _get_folder_size(self, folder_path: str) -> Tuple[int, int]:
        """Get total size and file count for a folder.
        
        Args:
            folder_path: Path to folder
            
        Returns:
            Tuple of (total_size_bytes, file_count)
        """
        try:
            total_size = 0
            file_count = 0
            
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        file_size = os.path.getsize(file_path)
                        total_size += file_size
                        file_count += 1
                    except (OSError, IOError):
                        continue
            
            return total_size, file_count
            
        except Exception as e:
            self.logger.error(f"Failed to get folder size for {folder_path}: {str(e)}")
            return 0, 0
    
    def _cleanup_old_files(self, folder_path: str, cutoff_time: datetime) -> Dict[str, int]:
        """Clean up files older than cutoff time.
        
        Args:
            folder_path: Path to folder to clean
            cutoff_time: Files older than this will be deleted
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            cleanup_stats = {
                'files_cleaned': 0,
                'space_freed': 0
            }
            
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                
                try:
                    # Check if file is older than cutoff
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < cutoff_time:
                        file_size = os.path.getsize(file_path)
                        os.unlink(file_path)
                        cleanup_stats['files_cleaned'] += 1
                        cleanup_stats['space_freed'] += file_size
                        self.logger.debug(f"Cleaned up old file: {file_path}")
                except Exception as e:
                    self.logger.warning(f"Could not clean up file {file_path}: {str(e)}")
            
            return cleanup_stats
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old files in {folder_path}: {str(e)}")
            return {'files_cleaned': 0, 'space_freed': 0}
