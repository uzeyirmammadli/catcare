"""
Temporary File Manager for efficient temporary file management and cleanup.

This service provides intelligent temporary file management with automatic cleanup,
resource monitoring, and efficient storage utilization.
"""

import atexit
import logging
import os
import shutil
import tempfile
import threading
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Generator
from threading import Lock, RLock

from flask import current_app


@dataclass
class TempFileInfo:
    """Temporary file information data class."""
    file_id: str
    file_path: str
    created_at: datetime
    last_accessed: datetime
    size_bytes: int
    purpose: str
    auto_cleanup: bool = True
    cleanup_after: timedelta = field(default_factory=lambda: timedelta(hours=1))
    tags: List[str] = field(default_factory=list)


@dataclass
class TempFileStats:
    """Temporary file statistics data class."""
    total_files: int = 0
    total_size_bytes: int = 0
    active_files: int = 0
    cleaned_files: int = 0
    cleanup_failures: int = 0
    disk_usage_mb: float = 0.0
    oldest_file_age_hours: float = 0.0


class TempFileManager:
    """Manager for temporary files with automatic cleanup and monitoring."""
    
    def __init__(self, temp_dir: Optional[str] = None, max_total_size: int = 500 * 1024 * 1024,
                 default_cleanup_after: int = 3600, cleanup_interval: int = 300):
        """Initialize the temporary file manager.
        
        Args:
            temp_dir: Directory for temporary files (defaults to system temp + app name)
            max_total_size: Maximum total size of temp files in bytes (500MB default)
            default_cleanup_after: Default cleanup time in seconds (1 hour default)
            cleanup_interval: Cleanup check interval in seconds (5 minutes default)
        """
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.max_total_size = max_total_size
        self.default_cleanup_after = timedelta(seconds=default_cleanup_after)
        self.cleanup_interval = cleanup_interval
        
        # Temporary directory setup
        if temp_dir is None:
            app_name = current_app.config.get('APP_NAME', 'catcare')
            temp_dir = os.path.join(tempfile.gettempdir(), f"{app_name}_temp")
        
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # File tracking
        self.temp_files: Dict[str, TempFileInfo] = {}
        self.files_lock = RLock()
        
        # Statistics
        self.stats = TempFileStats()
        self.stats_lock = Lock()
        
        # Cleanup management
        self.cleanup_thread: Optional[threading.Thread] = None
        self.cleanup_running = False
        self.shutdown_event = threading.Event()
        
        # Start cleanup thread
        self._start_cleanup_thread()
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
        
        self.logger.info(f"TempFileManager initialized with temp dir: {self.temp_dir}")
    
    def create_temp_file(self, suffix: str = '', prefix: str = 'temp_', 
                        purpose: str = 'general', auto_cleanup: bool = True,
                        cleanup_after: Optional[timedelta] = None,
                        tags: Optional[List[str]] = None) -> str:
        """Create a temporary file.
        
        Args:
            suffix: File suffix/extension
            prefix: File prefix
            purpose: Purpose description for the file
            auto_cleanup: Whether to automatically clean up the file
            cleanup_after: Time after which to clean up the file
            tags: Tags for categorizing the file
            
        Returns:
            Path to the created temporary file
            
        Raises:
            OSError: If file creation fails
            RuntimeError: If storage limit exceeded
        """
        try:
            # Check storage limits
            self._check_storage_limits()
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            
            # Create temporary file
            fd, temp_path = tempfile.mkstemp(
                suffix=suffix,
                prefix=f"{prefix}{file_id}_",
                dir=str(self.temp_dir)
            )
            os.close(fd)  # Close file descriptor, keep the file
            
            # Create file info
            file_info = TempFileInfo(
                file_id=file_id,
                file_path=temp_path,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=0,  # Will be updated when file is written
                purpose=purpose,
                auto_cleanup=auto_cleanup,
                cleanup_after=cleanup_after or self.default_cleanup_after,
                tags=tags or []
            )
            
            # Track the file
            with self.files_lock:
                self.temp_files[file_id] = file_info
            
            # Update statistics
            self._update_stats()
            
            self.logger.debug(f"Created temp file: {temp_path} (ID: {file_id}, purpose: {purpose})")
            return temp_path
            
        except Exception as e:
            self.logger.error(f"Failed to create temp file: {str(e)}")
            raise
    
    def create_temp_dir(self, prefix: str = 'temp_dir_', purpose: str = 'general',
                       auto_cleanup: bool = True, cleanup_after: Optional[timedelta] = None,
                       tags: Optional[List[str]] = None) -> str:
        """Create a temporary directory.
        
        Args:
            prefix: Directory prefix
            purpose: Purpose description for the directory
            auto_cleanup: Whether to automatically clean up the directory
            cleanup_after: Time after which to clean up the directory
            tags: Tags for categorizing the directory
            
        Returns:
            Path to the created temporary directory
            
        Raises:
            OSError: If directory creation fails
        """
        try:
            # Generate unique directory ID
            dir_id = str(uuid.uuid4())
            
            # Create temporary directory
            temp_dir_path = tempfile.mkdtemp(
                prefix=f"{prefix}{dir_id}_",
                dir=str(self.temp_dir)
            )
            
            # Create directory info (treat as special file)
            dir_info = TempFileInfo(
                file_id=dir_id,
                file_path=temp_dir_path,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=0,  # Will be calculated during cleanup
                purpose=f"directory_{purpose}",
                auto_cleanup=auto_cleanup,
                cleanup_after=cleanup_after or self.default_cleanup_after,
                tags=(tags or []) + ['directory']
            )
            
            # Track the directory
            with self.files_lock:
                self.temp_files[dir_id] = dir_info
            
            self.logger.debug(f"Created temp directory: {temp_dir_path} (ID: {dir_id})")
            return temp_dir_path
            
        except Exception as e:
            self.logger.error(f"Failed to create temp directory: {str(e)}")
            raise
    
    @contextmanager
    def temp_file(self, suffix: str = '', prefix: str = 'temp_', 
                 purpose: str = 'context_managed') -> Generator[str, None, None]:
        """Context manager for temporary files with automatic cleanup.
        
        Args:
            suffix: File suffix/extension
            prefix: File prefix
            purpose: Purpose description for the file
            
        Yields:
            Path to the temporary file
        """
        temp_path = None
        try:
            temp_path = self.create_temp_file(
                suffix=suffix,
                prefix=prefix,
                purpose=purpose,
                auto_cleanup=False  # We'll clean up manually
            )
            yield temp_path
        finally:
            if temp_path:
                self.cleanup_file(temp_path)
    
    @contextmanager
    def temp_dir(self, prefix: str = 'temp_dir_', 
                purpose: str = 'context_managed') -> Generator[str, None, None]:
        """Context manager for temporary directories with automatic cleanup.
        
        Args:
            prefix: Directory prefix
            purpose: Purpose description for the directory
            
        Yields:
            Path to the temporary directory
        """
        temp_dir_path = None
        try:
            temp_dir_path = self.create_temp_dir(
                prefix=prefix,
                purpose=purpose,
                auto_cleanup=False  # We'll clean up manually
            )
            yield temp_dir_path
        finally:
            if temp_dir_path:
                self.cleanup_file(temp_dir_path)
    
    def update_file_access(self, file_path: str) -> bool:
        """Update last access time for a temporary file.
        
        Args:
            file_path: Path to the temporary file
            
        Returns:
            True if file was found and updated, False otherwise
        """
        try:
            with self.files_lock:
                for file_info in self.temp_files.values():
                    if file_info.file_path == file_path:
                        file_info.last_accessed = datetime.now()
                        
                        # Update file size if it exists
                        if os.path.exists(file_path):
                            if os.path.isfile(file_path):
                                file_info.size_bytes = os.path.getsize(file_path)
                            elif os.path.isdir(file_path):
                                file_info.size_bytes = self._get_directory_size(file_path)
                        
                        return True
            
            return False
            
        except Exception as e:
            self.logger.debug(f"Failed to update file access: {str(e)}")
            return False
    
    def cleanup_file(self, file_path: str) -> bool:
        """Clean up a specific temporary file or directory.
        
        Args:
            file_path: Path to the file or directory to clean up
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            # Find and remove from tracking
            file_id_to_remove = None
            with self.files_lock:
                for file_id, file_info in self.temp_files.items():
                    if file_info.file_path == file_path:
                        file_id_to_remove = file_id
                        break
                
                if file_id_to_remove:
                    del self.temp_files[file_id_to_remove]
            
            # Remove from filesystem
            if os.path.exists(file_path):
                if os.path.isfile(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                
                self.logger.debug(f"Cleaned up temp file/dir: {file_path}")
                
                # Update statistics
                with self.stats_lock:
                    self.stats.cleaned_files += 1
                
                return True
            
            return False
            
        except Exception as e:
            self.logger.warning(f"Failed to cleanup temp file {file_path}: {str(e)}")
            with self.stats_lock:
                self.stats.cleanup_failures += 1
            return False
    
    def cleanup_by_purpose(self, purpose: str) -> int:
        """Clean up all temporary files with a specific purpose.
        
        Args:
            purpose: Purpose to clean up
            
        Returns:
            Number of files cleaned up
        """
        try:
            files_to_cleanup = []
            
            with self.files_lock:
                for file_info in self.temp_files.values():
                    if file_info.purpose == purpose:
                        files_to_cleanup.append(file_info.file_path)
            
            cleanup_count = 0
            for file_path in files_to_cleanup:
                if self.cleanup_file(file_path):
                    cleanup_count += 1
            
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} temp files with purpose '{purpose}'")
            
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup files by purpose: {str(e)}")
            return 0
    
    def cleanup_by_tags(self, tags: List[str]) -> int:
        """Clean up all temporary files with specific tags.
        
        Args:
            tags: List of tags to match
            
        Returns:
            Number of files cleaned up
        """
        try:
            files_to_cleanup = []
            
            with self.files_lock:
                for file_info in self.temp_files.values():
                    if any(tag in file_info.tags for tag in tags):
                        files_to_cleanup.append(file_info.file_path)
            
            cleanup_count = 0
            for file_path in files_to_cleanup:
                if self.cleanup_file(file_path):
                    cleanup_count += 1
            
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} temp files with tags {tags}")
            
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup files by tags: {str(e)}")
            return 0
    
    def cleanup_expired(self) -> int:
        """Clean up expired temporary files.
        
        Returns:
            Number of files cleaned up
        """
        try:
            now = datetime.now()
            files_to_cleanup = []
            
            with self.files_lock:
                for file_info in self.temp_files.values():
                    if file_info.auto_cleanup:
                        expiry_time = file_info.created_at + file_info.cleanup_after
                        if now > expiry_time:
                            files_to_cleanup.append(file_info.file_path)
            
            cleanup_count = 0
            for file_path in files_to_cleanup:
                if self.cleanup_file(file_path):
                    cleanup_count += 1
            
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} expired temp files")
            
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup expired files: {str(e)}")
            return 0
    
    def cleanup_all(self) -> int:
        """Clean up all temporary files.
        
        Returns:
            Number of files cleaned up
        """
        try:
            files_to_cleanup = []
            
            with self.files_lock:
                files_to_cleanup = list(self.temp_files.keys())
            
            cleanup_count = 0
            for file_id in files_to_cleanup:
                with self.files_lock:
                    file_info = self.temp_files.get(file_id)
                    if file_info and self.cleanup_file(file_info.file_path):
                        cleanup_count += 1
            
            # Also clean up any orphaned files in temp directory
            orphaned_count = self._cleanup_orphaned_files()
            cleanup_count += orphaned_count
            
            if cleanup_count > 0:
                self.logger.info(f"Cleaned up {cleanup_count} temp files (including {orphaned_count} orphaned)")
            
            return cleanup_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup all files: {str(e)}")
            return 0
    
    def get_temp_file_info(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Get information about a temporary file.
        
        Args:
            file_path: Path to the temporary file
            
        Returns:
            Dictionary with file information or None if not found
        """
        try:
            with self.files_lock:
                for file_info in self.temp_files.values():
                    if file_info.file_path == file_path:
                        return {
                            'file_id': file_info.file_id,
                            'file_path': file_info.file_path,
                            'created_at': file_info.created_at.isoformat(),
                            'last_accessed': file_info.last_accessed.isoformat(),
                            'size_bytes': file_info.size_bytes,
                            'size_mb': file_info.size_bytes / 1024 / 1024,
                            'purpose': file_info.purpose,
                            'auto_cleanup': file_info.auto_cleanup,
                            'cleanup_after_seconds': file_info.cleanup_after.total_seconds(),
                            'tags': file_info.tags,
                            'age_seconds': (datetime.now() - file_info.created_at).total_seconds(),
                            'expires_at': (file_info.created_at + file_info.cleanup_after).isoformat() if file_info.auto_cleanup else None
                        }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get temp file info: {str(e)}")
            return None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get temporary file statistics.
        
        Returns:
            Dictionary containing statistics
        """
        try:
            self._update_stats()
            
            with self.stats_lock:
                return {
                    'total_files': self.stats.total_files,
                    'active_files': self.stats.active_files,
                    'cleaned_files': self.stats.cleaned_files,
                    'cleanup_failures': self.stats.cleanup_failures,
                    'total_size_bytes': self.stats.total_size_bytes,
                    'disk_usage_mb': self.stats.disk_usage_mb,
                    'max_total_size_mb': self.max_total_size / 1024 / 1024,
                    'usage_percentage': (self.stats.total_size_bytes / self.max_total_size * 100) if self.max_total_size > 0 else 0,
                    'oldest_file_age_hours': self.stats.oldest_file_age_hours,
                    'temp_directory': str(self.temp_dir),
                    'cleanup_interval_seconds': self.cleanup_interval,
                    'default_cleanup_after_seconds': self.default_cleanup_after.total_seconds()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get temp file stats: {str(e)}")
            return {'error': str(e)}
    
    def list_temp_files(self, purpose: Optional[str] = None, 
                       tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List temporary files with optional filtering.
        
        Args:
            purpose: Filter by purpose
            tags: Filter by tags
            
        Returns:
            List of file information dictionaries
        """
        try:
            files_list = []
            
            with self.files_lock:
                for file_info in self.temp_files.values():
                    # Apply filters
                    if purpose and file_info.purpose != purpose:
                        continue
                    
                    if tags and not any(tag in file_info.tags for tag in tags):
                        continue
                    
                    files_list.append({
                        'file_id': file_info.file_id,
                        'file_path': file_info.file_path,
                        'created_at': file_info.created_at.isoformat(),
                        'last_accessed': file_info.last_accessed.isoformat(),
                        'size_bytes': file_info.size_bytes,
                        'purpose': file_info.purpose,
                        'tags': file_info.tags,
                        'age_seconds': (datetime.now() - file_info.created_at).total_seconds(),
                        'exists': os.path.exists(file_info.file_path)
                    })
            
            # Sort by creation time (newest first)
            files_list.sort(key=lambda x: x['created_at'], reverse=True)
            return files_list
            
        except Exception as e:
            self.logger.error(f"Failed to list temp files: {str(e)}")
            return []
    
    def shutdown(self) -> None:
        """Shutdown the temporary file manager."""
        try:
            self.logger.info("Shutting down TempFileManager...")
            
            # Stop cleanup thread
            self.shutdown_event.set()
            self.cleanup_running = False
            
            if self.cleanup_thread and self.cleanup_thread.is_alive():
                self.cleanup_thread.join(timeout=5.0)
            
            # Clean up all files
            self.cleanup_all()
            
            self.logger.info("TempFileManager shutdown complete")
            
        except Exception as e:
            self.logger.error(f"TempFileManager shutdown failed: {str(e)}")
    
    def _check_storage_limits(self) -> None:
        """Check if storage limits would be exceeded."""
        current_size = self._calculate_total_size()
        if current_size > self.max_total_size:
            # Try to clean up expired files first
            self.cleanup_expired()
            
            # Check again
            current_size = self._calculate_total_size()
            if current_size > self.max_total_size:
                raise RuntimeError(f"Temporary storage limit exceeded: {current_size} > {self.max_total_size}")
    
    def _start_cleanup_thread(self) -> None:
        """Start the background cleanup thread."""
        try:
            self.cleanup_running = True
            self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
            self.cleanup_thread.start()
            self.logger.debug("Cleanup thread started")
        except Exception as e:
            self.logger.error(f"Failed to start cleanup thread: {str(e)}")
    
    def _cleanup_worker(self) -> None:
        """Background cleanup worker thread."""
        self.logger.debug("Cleanup worker thread started")
        
        while self.cleanup_running and not self.shutdown_event.is_set():
            try:
                # Wait for cleanup interval or shutdown signal
                if self.shutdown_event.wait(timeout=self.cleanup_interval):
                    break
                
                # Perform cleanup
                self.cleanup_expired()
                
                # Update statistics
                self._update_stats()
                
            except Exception as e:
                self.logger.error(f"Cleanup worker error: {str(e)}")
        
        self.logger.debug("Cleanup worker thread stopped")
    
    def _calculate_total_size(self) -> int:
        """Calculate total size of all temporary files."""
        total_size = 0
        
        with self.files_lock:
            for file_info in self.temp_files.values():
                if os.path.exists(file_info.file_path):
                    if os.path.isfile(file_info.file_path):
                        file_info.size_bytes = os.path.getsize(file_info.file_path)
                    elif os.path.isdir(file_info.file_path):
                        file_info.size_bytes = self._get_directory_size(file_info.file_path)
                    
                    total_size += file_info.size_bytes
        
        return total_size
    
    def _get_directory_size(self, directory_path: str) -> int:
        """Get total size of a directory."""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(directory_path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, IOError):
                        pass
            return total_size
        except Exception:
            return 0
    
    def _cleanup_orphaned_files(self) -> int:
        """Clean up orphaned files in temp directory that aren't tracked."""
        try:
            tracked_paths = set()
            with self.files_lock:
                tracked_paths = {file_info.file_path for file_info in self.temp_files.values()}
            
            orphaned_count = 0
            
            # Check all files/directories in temp directory
            if self.temp_dir.exists():
                for item in self.temp_dir.iterdir():
                    if str(item) not in tracked_paths:
                        try:
                            if item.is_file():
                                item.unlink()
                            elif item.is_dir():
                                shutil.rmtree(item)
                            orphaned_count += 1
                        except Exception as e:
                            self.logger.debug(f"Failed to remove orphaned item {item}: {str(e)}")
            
            return orphaned_count
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup orphaned files: {str(e)}")
            return 0
    
    def _update_stats(self) -> None:
        """Update statistics."""
        try:
            now = datetime.now()
            
            with self.stats_lock:
                with self.files_lock:
                    self.stats.active_files = len(self.temp_files)
                    self.stats.total_size_bytes = sum(
                        file_info.size_bytes for file_info in self.temp_files.values()
                    )
                    self.stats.disk_usage_mb = self.stats.total_size_bytes / 1024 / 1024
                    
                    # Find oldest file
                    if self.temp_files:
                        oldest_file = min(self.temp_files.values(), key=lambda x: x.created_at)
                        self.stats.oldest_file_age_hours = (now - oldest_file.created_at).total_seconds() / 3600
                    else:
                        self.stats.oldest_file_age_hours = 0
                
        except Exception as e:
            self.logger.debug(f"Stats update failed: {str(e)}")


# Global temp file manager instance
_temp_file_manager: Optional[TempFileManager] = None


def get_temp_file_manager() -> TempFileManager:
    """Get the global temp file manager instance.
    
    Returns:
        TempFileManager instance
    """
    global _temp_file_manager
    if _temp_file_manager is None:
        _temp_file_manager = TempFileManager()
    return _temp_file_manager


def shutdown_temp_file_manager() -> None:
    """Shutdown the global temp file manager."""
    global _temp_file_manager
    if _temp_file_manager is not None:
        _temp_file_manager.shutdown()
        _temp_file_manager = None