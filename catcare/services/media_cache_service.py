"""
Media Cache Service for efficient caching of processed thumbnails and metadata.

This service provides intelligent caching mechanisms to improve performance
and reduce redundant processing operations.
"""

import hashlib
import json
import logging
import os
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
from threading import Lock, RLock
from dataclasses import dataclass, field
from pathlib import Path

from flask import current_app


@dataclass
class CacheEntry:
    """Cache entry data class."""
    key: str
    data: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    expires_at: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class CacheStats:
    """Cache statistics data class."""
    total_entries: int = 0
    total_size_bytes: int = 0
    hit_count: int = 0
    miss_count: int = 0
    eviction_count: int = 0
    hit_rate: float = 0.0
    memory_usage_mb: float = 0.0
    disk_usage_mb: float = 0.0


class MediaCacheService:
    """Service for caching processed media, thumbnails, and metadata."""
    
    def __init__(self, cache_dir: Optional[str] = None, max_memory_size: int = 100 * 1024 * 1024,
                 max_disk_size: int = 1024 * 1024 * 1024, default_ttl: int = 3600):
        """Initialize the media cache service.
        
        Args:
            cache_dir: Directory for disk cache (defaults to uploads/cache)
            max_memory_size: Maximum memory cache size in bytes (100MB default)
            max_disk_size: Maximum disk cache size in bytes (1GB default)
            default_ttl: Default time-to-live in seconds (1 hour default)
        """
        self.logger = logging.getLogger(__name__)
        
        # Cache configuration
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        self.default_ttl = default_ttl
        
        # Cache directories
        if cache_dir is None:
            cache_dir = os.path.join(current_app.config.get("UPLOAD_FOLDER", "uploads"), "cache")
        
        self.cache_dir = Path(cache_dir)
        self.thumbnail_cache_dir = self.cache_dir / "thumbnails"
        self.metadata_cache_dir = self.cache_dir / "metadata"
        self.temp_cache_dir = self.cache_dir / "temp"
        
        # Create cache directories
        self._ensure_cache_directories()
        
        # Memory cache
        self.memory_cache: Dict[str, CacheEntry] = {}
        self.memory_lock = RLock()
        
        # Cache statistics
        self.stats = CacheStats()
        self.stats_lock = Lock()
        
        # Cache maintenance
        self.last_cleanup = datetime.now()
        self.cleanup_interval = timedelta(minutes=30)
        
        self.logger.info(f"MediaCacheService initialized with {max_memory_size // 1024 // 1024}MB memory cache")
    
    def get_thumbnail(self, image_path: str, size_label: str, 
                     generation_options: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Get cached thumbnail or generate if not exists.
        
        Args:
            image_path: Path to original image
            size_label: Thumbnail size label (e.g., "300x300")
            generation_options: Options for thumbnail generation
            
        Returns:
            Path to cached thumbnail or None if generation failed
        """
        try:
            # Generate cache key
            cache_key = self._generate_thumbnail_cache_key(image_path, size_label, generation_options)
            
            # Check memory cache first
            cached_path = self._get_from_memory_cache(cache_key)
            if cached_path and os.path.exists(cached_path):
                self.logger.debug(f"Thumbnail cache hit (memory): {cache_key}")
                return cached_path
            
            # Check disk cache
            cached_path = self._get_thumbnail_from_disk(cache_key)
            if cached_path and os.path.exists(cached_path):
                # Store in memory cache for faster access
                self._store_in_memory_cache(cache_key, cached_path, tags=['thumbnail'])
                self.logger.debug(f"Thumbnail cache hit (disk): {cache_key}")
                return cached_path
            
            # Cache miss - generate thumbnail
            self.logger.debug(f"Thumbnail cache miss: {cache_key}")
            generated_path = self._generate_and_cache_thumbnail(
                image_path, size_label, cache_key, generation_options
            )
            
            return generated_path
            
        except Exception as e:
            self.logger.error(f"Thumbnail caching failed: {str(e)}")
            return None
    
    def get_metadata(self, file_path: str, extraction_options: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Get cached metadata or extract if not exists.
        
        Args:
            file_path: Path to media file
            extraction_options: Options for metadata extraction
            
        Returns:
            Cached or extracted metadata dictionary
        """
        try:
            # Generate cache key
            cache_key = self._generate_metadata_cache_key(file_path, extraction_options)
            
            # Check memory cache first
            cached_metadata = self._get_from_memory_cache(cache_key)
            if cached_metadata is not None:
                self.logger.debug(f"Metadata cache hit (memory): {cache_key}")
                return cached_metadata
            
            # Check disk cache
            cached_metadata = self._get_metadata_from_disk(cache_key)
            if cached_metadata is not None:
                # Store in memory cache for faster access
                self._store_in_memory_cache(cache_key, cached_metadata, tags=['metadata'])
                self.logger.debug(f"Metadata cache hit (disk): {cache_key}")
                return cached_metadata
            
            # Cache miss - extract metadata
            self.logger.debug(f"Metadata cache miss: {cache_key}")
            extracted_metadata = self._extract_and_cache_metadata(
                file_path, cache_key, extraction_options
            )
            
            return extracted_metadata
            
        except Exception as e:
            self.logger.error(f"Metadata caching failed: {str(e)}")
            return None
    
    def cache_processed_media(self, original_path: str, processed_path: str, 
                            processing_options: Dict[str, Any]) -> bool:
        """Cache processed media file.
        
        Args:
            original_path: Path to original file
            processed_path: Path to processed file
            processing_options: Processing options used
            
        Returns:
            True if caching successful, False otherwise
        """
        try:
            cache_key = self._generate_processed_media_cache_key(original_path, processing_options)
            
            # Copy processed file to cache
            cached_path = self.temp_cache_dir / f"{cache_key}.jpg"
            
            import shutil
            shutil.copy2(processed_path, cached_path)
            
            # Store in memory cache
            self._store_in_memory_cache(cache_key, str(cached_path), tags=['processed_media'])
            
            self.logger.debug(f"Cached processed media: {cache_key}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cache processed media: {str(e)}")
            return False
    
    def get_cached_processed_media(self, original_path: str, 
                                 processing_options: Dict[str, Any]) -> Optional[str]:
        """Get cached processed media file.
        
        Args:
            original_path: Path to original file
            processing_options: Processing options used
            
        Returns:
            Path to cached processed file or None if not found
        """
        try:
            cache_key = self._generate_processed_media_cache_key(original_path, processing_options)
            
            # Check memory cache
            cached_path = self._get_from_memory_cache(cache_key)
            if cached_path and os.path.exists(cached_path):
                self.logger.debug(f"Processed media cache hit: {cache_key}")
                return cached_path
            
            # Check disk cache
            cached_path = self.temp_cache_dir / f"{cache_key}.jpg"
            if cached_path.exists():
                # Store in memory cache
                self._store_in_memory_cache(cache_key, str(cached_path), tags=['processed_media'])
                self.logger.debug(f"Processed media cache hit (disk): {cache_key}")
                return str(cached_path)
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to get cached processed media: {str(e)}")
            return None
    
    def invalidate_cache(self, file_path: str) -> int:
        """Invalidate all cache entries for a specific file.
        
        Args:
            file_path: Path to file whose cache entries should be invalidated
            
        Returns:
            Number of cache entries invalidated
        """
        try:
            file_hash = self._get_file_hash(file_path)
            invalidated_count = 0
            
            with self.memory_lock:
                keys_to_remove = []
                for key, entry in self.memory_cache.items():
                    if file_hash in key:
                        keys_to_remove.append(key)
                
                for key in keys_to_remove:
                    del self.memory_cache[key]
                    invalidated_count += 1
            
            # Also remove from disk cache
            for cache_subdir in [self.thumbnail_cache_dir, self.metadata_cache_dir, self.temp_cache_dir]:
                for cache_file in cache_subdir.glob(f"*{file_hash}*"):
                    try:
                        cache_file.unlink()
                        invalidated_count += 1
                    except OSError:
                        pass
            
            if invalidated_count > 0:
                self.logger.info(f"Invalidated {invalidated_count} cache entries for {file_path}")
            
            return invalidated_count
            
        except Exception as e:
            self.logger.error(f"Cache invalidation failed: {str(e)}")
            return 0
    
    def clear_cache(self, cache_type: Optional[str] = None) -> Dict[str, int]:
        """Clear cache entries.
        
        Args:
            cache_type: Type of cache to clear ('memory', 'disk', or None for both)
            
        Returns:
            Dictionary with counts of cleared entries
        """
        cleared_counts = {'memory': 0, 'disk': 0}
        
        try:
            if cache_type in [None, 'memory']:
                with self.memory_lock:
                    cleared_counts['memory'] = len(self.memory_cache)
                    self.memory_cache.clear()
            
            if cache_type in [None, 'disk']:
                for cache_subdir in [self.thumbnail_cache_dir, self.metadata_cache_dir, self.temp_cache_dir]:
                    for cache_file in cache_subdir.iterdir():
                        if cache_file.is_file():
                            try:
                                cache_file.unlink()
                                cleared_counts['disk'] += 1
                            except OSError:
                                pass
            
            # Reset statistics
            with self.stats_lock:
                if cache_type in [None, 'memory']:
                    self.stats.total_entries = 0
                    self.stats.total_size_bytes = 0
            
            self.logger.info(f"Cleared cache: {cleared_counts}")
            return cleared_counts
            
        except Exception as e:
            self.logger.error(f"Cache clearing failed: {str(e)}")
            return cleared_counts
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        try:
            self._update_stats()
            
            with self.stats_lock:
                total_requests = self.stats.hit_count + self.stats.miss_count
                hit_rate = (self.stats.hit_count / total_requests * 100) if total_requests > 0 else 0
                
                return {
                    'memory_cache': {
                        'entries': self.stats.total_entries,
                        'size_mb': self.stats.memory_usage_mb,
                        'max_size_mb': self.max_memory_size / 1024 / 1024
                    },
                    'disk_cache': {
                        'size_mb': self.stats.disk_usage_mb,
                        'max_size_mb': self.max_disk_size / 1024 / 1024
                    },
                    'performance': {
                        'hit_count': self.stats.hit_count,
                        'miss_count': self.stats.miss_count,
                        'hit_rate_percent': hit_rate,
                        'eviction_count': self.stats.eviction_count
                    },
                    'directories': {
                        'cache_dir': str(self.cache_dir),
                        'thumbnail_cache_dir': str(self.thumbnail_cache_dir),
                        'metadata_cache_dir': str(self.metadata_cache_dir)
                    }
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get cache stats: {str(e)}")
            return {'error': str(e)}
    
    def optimize_cache(self) -> Dict[str, Any]:
        """Optimize cache by removing expired and least-used entries.
        
        Returns:
            Dictionary with optimization results
        """
        try:
            optimization_results = {
                'expired_entries_removed': 0,
                'lru_entries_removed': 0,
                'disk_files_cleaned': 0,
                'space_freed_mb': 0
            }
            
            now = datetime.now()
            
            # Clean expired entries from memory cache
            with self.memory_lock:
                expired_keys = []
                for key, entry in self.memory_cache.items():
                    if entry.expires_at and entry.expires_at < now:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self.memory_cache[key]
                    optimization_results['expired_entries_removed'] += 1
            
            # Clean LRU entries if memory cache is too large
            current_size = self._calculate_memory_cache_size()
            if current_size > self.max_memory_size:
                lru_removed = self._evict_lru_entries(current_size - self.max_memory_size)
                optimization_results['lru_entries_removed'] = lru_removed
            
            # Clean old disk cache files
            cutoff_time = now - timedelta(days=7)  # Remove files older than 7 days
            for cache_subdir in [self.thumbnail_cache_dir, self.metadata_cache_dir, self.temp_cache_dir]:
                for cache_file in cache_subdir.iterdir():
                    if cache_file.is_file():
                        try:
                            file_mtime = datetime.fromtimestamp(cache_file.stat().st_mtime)
                            if file_mtime < cutoff_time:
                                file_size = cache_file.stat().st_size
                                cache_file.unlink()
                                optimization_results['disk_files_cleaned'] += 1
                                optimization_results['space_freed_mb'] += file_size / 1024 / 1024
                        except OSError:
                            pass
            
            self.logger.info(f"Cache optimization completed: {optimization_results}")
            return optimization_results
            
        except Exception as e:
            self.logger.error(f"Cache optimization failed: {str(e)}")
            return {'error': str(e)}
    
    def _ensure_cache_directories(self) -> None:
        """Ensure all cache directories exist."""
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.thumbnail_cache_dir.mkdir(parents=True, exist_ok=True)
            self.metadata_cache_dir.mkdir(parents=True, exist_ok=True)
            self.temp_cache_dir.mkdir(parents=True, exist_ok=True)
            
            self.logger.debug(f"Cache directories ensured: {self.cache_dir}")
            
        except Exception as e:
            self.logger.error(f"Failed to create cache directories: {str(e)}")
            raise
    
    def _generate_thumbnail_cache_key(self, image_path: str, size_label: str, 
                                    options: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for thumbnail."""
        file_hash = self._get_file_hash(image_path)
        options_hash = self._get_options_hash(options or {})
        return f"thumb_{file_hash}_{size_label}_{options_hash}"
    
    def _generate_metadata_cache_key(self, file_path: str, 
                                   options: Optional[Dict[str, Any]]) -> str:
        """Generate cache key for metadata."""
        file_hash = self._get_file_hash(file_path)
        options_hash = self._get_options_hash(options or {})
        return f"meta_{file_hash}_{options_hash}"
    
    def _generate_processed_media_cache_key(self, original_path: str, 
                                          options: Dict[str, Any]) -> str:
        """Generate cache key for processed media."""
        file_hash = self._get_file_hash(original_path)
        options_hash = self._get_options_hash(options)
        return f"proc_{file_hash}_{options_hash}"
    
    def _get_file_hash(self, file_path: str) -> str:
        """Get hash of file for cache key generation."""
        try:
            # Use file path, size, and modification time for hash
            stat = os.stat(file_path)
            hash_input = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(hash_input.encode()).hexdigest()[:16]
        except OSError:
            # Fallback to just file path hash
            return hashlib.md5(file_path.encode()).hexdigest()[:16]
    
    def _get_options_hash(self, options: Dict[str, Any]) -> str:
        """Get hash of options dictionary."""
        options_str = json.dumps(options, sort_keys=True, default=str)
        return hashlib.md5(options_str.encode()).hexdigest()[:8]
    
    def _get_from_memory_cache(self, cache_key: str) -> Any:
        """Get entry from memory cache."""
        with self.memory_lock:
            entry = self.memory_cache.get(cache_key)
            if entry is None:
                with self.stats_lock:
                    self.stats.miss_count += 1
                return None
            
            # Check expiration
            if entry.expires_at and entry.expires_at < datetime.now():
                del self.memory_cache[cache_key]
                with self.stats_lock:
                    self.stats.miss_count += 1
                return None
            
            # Update access info
            entry.last_accessed = datetime.now()
            entry.access_count += 1
            
            with self.stats_lock:
                self.stats.hit_count += 1
            
            return entry.data
    
    def _store_in_memory_cache(self, cache_key: str, data: Any, 
                             ttl: Optional[int] = None, tags: Optional[List[str]] = None) -> None:
        """Store entry in memory cache."""
        try:
            # Calculate data size
            data_size = len(pickle.dumps(data))
            
            # Check if we need to evict entries
            current_size = self._calculate_memory_cache_size()
            if current_size + data_size > self.max_memory_size:
                self._evict_lru_entries(data_size)
            
            # Create cache entry
            expires_at = None
            if ttl is not None:
                expires_at = datetime.now() + timedelta(seconds=ttl)
            elif self.default_ttl > 0:
                expires_at = datetime.now() + timedelta(seconds=self.default_ttl)
            
            entry = CacheEntry(
                key=cache_key,
                data=data,
                created_at=datetime.now(),
                last_accessed=datetime.now(),
                size_bytes=data_size,
                expires_at=expires_at,
                tags=tags or []
            )
            
            with self.memory_lock:
                self.memory_cache[cache_key] = entry
            
        except Exception as e:
            self.logger.warning(f"Failed to store in memory cache: {str(e)}")
    
    def _get_thumbnail_from_disk(self, cache_key: str) -> Optional[str]:
        """Get thumbnail from disk cache."""
        try:
            cache_file = self.thumbnail_cache_dir / f"{cache_key}.jpg"
            if cache_file.exists():
                # Update access time
                cache_file.touch()
                return str(cache_file)
            return None
        except Exception as e:
            self.logger.debug(f"Disk thumbnail cache miss: {str(e)}")
            return None
    
    def _get_metadata_from_disk(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get metadata from disk cache."""
        try:
            cache_file = self.metadata_cache_dir / f"{cache_key}.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    metadata = json.load(f)
                # Update access time
                cache_file.touch()
                return metadata
            return None
        except Exception as e:
            self.logger.debug(f"Disk metadata cache miss: {str(e)}")
            return None
    
    def _generate_and_cache_thumbnail(self, image_path: str, size_label: str, 
                                    cache_key: str, options: Optional[Dict[str, Any]]) -> Optional[str]:
        """Generate thumbnail and cache it."""
        try:
            # Import here to avoid circular imports
            from .media_processing_service import ThumbnailGenerator
            
            # Parse size label
            width, height = map(int, size_label.split('x'))
            
            # Generate thumbnail
            thumbnail_generator = ThumbnailGenerator()
            thumbnails = thumbnail_generator.generate_thumbnails(
                image_path, 
                sizes=[(width, height)],
                output_dir=str(self.thumbnail_cache_dir)
            )
            
            if thumbnails:
                thumbnail_info = thumbnails[0]
                cached_path = str(self.thumbnail_cache_dir / thumbnail_info.filename)
                
                # Rename to cache key format
                final_cache_path = str(self.thumbnail_cache_dir / f"{cache_key}.jpg")
                os.rename(cached_path, final_cache_path)
                
                # Store in memory cache
                self._store_in_memory_cache(cache_key, final_cache_path, tags=['thumbnail'])
                
                return final_cache_path
            
            return None
            
        except Exception as e:
            self.logger.error(f"Thumbnail generation and caching failed: {str(e)}")
            return None
    
    def _extract_and_cache_metadata(self, file_path: str, cache_key: str, 
                                  options: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Extract metadata and cache it."""
        try:
            # Import here to avoid circular imports
            from .media_processing_service import EXIFExtractor
            
            # Extract metadata
            exif_extractor = EXIFExtractor()
            metadata = exif_extractor.extract_exif_data(file_path)
            
            # Add additional metadata
            enhanced_metadata = {
                'exif_data': metadata,
                'extracted_at': datetime.now().isoformat(),
                'file_path': file_path,
                'file_size': os.path.getsize(file_path) if os.path.exists(file_path) else 0
            }
            
            # Cache to disk
            cache_file = self.metadata_cache_dir / f"{cache_key}.json"
            with open(cache_file, 'w') as f:
                json.dump(enhanced_metadata, f, indent=2, default=str)
            
            # Store in memory cache
            self._store_in_memory_cache(cache_key, enhanced_metadata, tags=['metadata'])
            
            return enhanced_metadata
            
        except Exception as e:
            self.logger.error(f"Metadata extraction and caching failed: {str(e)}")
            return None
    
    def _calculate_memory_cache_size(self) -> int:
        """Calculate total size of memory cache."""
        with self.memory_lock:
            return sum(entry.size_bytes for entry in self.memory_cache.values())
    
    def _evict_lru_entries(self, target_size: int) -> int:
        """Evict least recently used entries to free up space.
        
        Args:
            target_size: Amount of space to free up in bytes
            
        Returns:
            Number of entries evicted
        """
        evicted_count = 0
        freed_size = 0
        
        with self.memory_lock:
            # Sort entries by last accessed time (LRU first)
            sorted_entries = sorted(
                self.memory_cache.items(),
                key=lambda x: x[1].last_accessed
            )
            
            for key, entry in sorted_entries:
                if freed_size >= target_size:
                    break
                
                del self.memory_cache[key]
                freed_size += entry.size_bytes
                evicted_count += 1
        
        with self.stats_lock:
            self.stats.eviction_count += evicted_count
        
        if evicted_count > 0:
            self.logger.debug(f"Evicted {evicted_count} LRU entries, freed {freed_size} bytes")
        
        return evicted_count
    
    def _update_stats(self) -> None:
        """Update cache statistics."""
        try:
            with self.stats_lock:
                with self.memory_lock:
                    self.stats.total_entries = len(self.memory_cache)
                    self.stats.total_size_bytes = sum(entry.size_bytes for entry in self.memory_cache.values())
                    self.stats.memory_usage_mb = self.stats.total_size_bytes / 1024 / 1024
                
                # Calculate disk usage
                disk_size = 0
                for cache_subdir in [self.thumbnail_cache_dir, self.metadata_cache_dir, self.temp_cache_dir]:
                    for cache_file in cache_subdir.iterdir():
                        if cache_file.is_file():
                            try:
                                disk_size += cache_file.stat().st_size
                            except OSError:
                                pass
                
                self.stats.disk_usage_mb = disk_size / 1024 / 1024
                
        except Exception as e:
            self.logger.debug(f"Stats update failed: {str(e)}")


# Global cache service instance
_cache_service: Optional[MediaCacheService] = None


def get_cache_service() -> MediaCacheService:
    """Get the global cache service instance.
    
    Returns:
        MediaCacheService instance
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = MediaCacheService()
    return _cache_service