"""
CDN Service for optimized media delivery and caching.

This service provides CDN integration capabilities for efficient media delivery,
including URL generation, cache management, and performance optimization.
"""

import hashlib
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Tuple
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, field

from flask import current_app, request


@dataclass
class CDNConfig:
    """CDN configuration data class."""
    enabled: bool = False
    base_url: str = ""
    cache_control_max_age: int = 86400  # 24 hours
    thumbnail_max_age: int = 2592000  # 30 days
    metadata_max_age: int = 3600  # 1 hour
    enable_compression: bool = True
    enable_webp: bool = True
    enable_progressive_jpeg: bool = True
    quality_levels: Dict[str, int] = field(default_factory=lambda: {
        'thumbnail': 85,
        'medium': 90,
        'high': 95
    })


@dataclass
class CDNStats:
    """CDN statistics data class."""
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    bytes_served: int = 0
    bandwidth_saved: int = 0
    hit_rate: float = 0.0
    average_response_time: float = 0.0


class CDNService:
    """Service for CDN integration and optimized media delivery."""
    
    def __init__(self, config: Optional[CDNConfig] = None):
        """Initialize the CDN service.
        
        Args:
            config: CDN configuration (defaults to app config)
        """
        self.logger = logging.getLogger(__name__)
        
        # Load configuration
        if config is None:
            config = self._load_config_from_app()
        
        self.config = config
        
        # Statistics
        self.stats = CDNStats()
        
        # URL cache for performance
        self.url_cache: Dict[str, Tuple[str, datetime]] = {}
        self.url_cache_ttl = timedelta(hours=1)
        
        # Supported image formats for optimization
        self.supported_formats = {
            'jpeg': ['jpg', 'jpeg'],
            'png': ['png'],
            'webp': ['webp'],
            'gif': ['gif']
        }
        
        # Quality presets
        self.quality_presets = {
            'thumbnail': {'quality': 85, 'progressive': True, 'optimize': True},
            'preview': {'quality': 90, 'progressive': True, 'optimize': True},
            'full': {'quality': 95, 'progressive': True, 'optimize': True}
        }
        
        self.logger.info(f"CDNService initialized (enabled: {self.config.enabled})")
    
    def get_media_url(self, file_path: str, optimization: Optional[str] = None,
                     format_hint: Optional[str] = None, cache_bust: bool = False) -> str:
        """Get optimized CDN URL for media file.
        
        Args:
            file_path: Original file path
            optimization: Optimization level ('thumbnail', 'preview', 'full')
            format_hint: Preferred format ('webp', 'jpeg', 'png')
            cache_bust: Whether to add cache busting parameter
            
        Returns:
            CDN URL or original URL if CDN disabled
        """
        try:
            # If CDN is disabled, return original URL
            if not self.config.enabled:
                return self._get_local_url(file_path)
            
            # Check URL cache first
            cache_key = f"{file_path}_{optimization}_{format_hint}_{cache_bust}"
            cached_url, cached_time = self.url_cache.get(cache_key, (None, None))
            
            if cached_url and cached_time and datetime.now() - cached_time < self.url_cache_ttl:
                return cached_url
            
            # Generate CDN URL
            cdn_url = self._generate_cdn_url(file_path, optimization, format_hint, cache_bust)
            
            # Cache the URL
            self.url_cache[cache_key] = (cdn_url, datetime.now())
            
            # Clean up old cache entries periodically
            if len(self.url_cache) > 1000:
                self._cleanup_url_cache()
            
            return cdn_url
            
        except Exception as e:
            self.logger.error(f"Failed to generate CDN URL for {file_path}: {str(e)}")
            return self._get_local_url(file_path)
    
    def get_thumbnail_url(self, file_path: str, size: str = "300x300",
                         format_hint: Optional[str] = None) -> str:
        """Get CDN URL for thumbnail with specific size.
        
        Args:
            file_path: Original file path
            size: Thumbnail size (e.g., "300x300", "150x150")
            format_hint: Preferred format
            
        Returns:
            CDN URL for thumbnail
        """
        try:
            if not self.config.enabled:
                return self._get_local_thumbnail_url(file_path, size)
            
            # Generate thumbnail-specific CDN URL
            base_url = self.config.base_url.rstrip('/')
            
            # Extract file info
            file_name = os.path.basename(file_path)
            file_base, file_ext = os.path.splitext(file_name)
            
            # Determine output format
            output_format = self._determine_output_format(format_hint, file_ext)
            
            # Build CDN URL with thumbnail parameters
            cdn_path = f"/thumbnails/{size}/{file_base}.{output_format}"
            
            # Add optimization parameters
            params = []
            if self.config.enable_compression:
                params.append(f"quality={self.config.quality_levels['thumbnail']}")
            if self.config.enable_progressive_jpeg and output_format == 'jpg':
                params.append("progressive=true")
            
            query_string = "&".join(params) if params else ""
            cdn_url = f"{base_url}{cdn_path}"
            if query_string:
                cdn_url += f"?{query_string}"
            
            return cdn_url
            
        except Exception as e:
            self.logger.error(f"Failed to generate thumbnail CDN URL: {str(e)}")
            return self._get_local_thumbnail_url(file_path, size)
    
    def get_responsive_urls(self, file_path: str, sizes: List[str],
                          format_hint: Optional[str] = None) -> Dict[str, str]:
        """Get responsive image URLs for different sizes.
        
        Args:
            file_path: Original file path
            sizes: List of sizes (e.g., ["300x300", "600x400", "1200x800"])
            format_hint: Preferred format
            
        Returns:
            Dictionary mapping sizes to CDN URLs
        """
        try:
            responsive_urls = {}
            
            for size in sizes:
                responsive_urls[size] = self.get_thumbnail_url(
                    file_path, size, format_hint
                )
            
            return responsive_urls
            
        except Exception as e:
            self.logger.error(f"Failed to generate responsive URLs: {str(e)}")
            return {}
    
    def invalidate_cache(self, file_path: str) -> bool:
        """Invalidate CDN cache for a specific file.
        
        Args:
            file_path: File path to invalidate
            
        Returns:
            True if invalidation successful, False otherwise
        """
        try:
            if not self.config.enabled:
                return True  # No CDN cache to invalidate
            
            # Remove from URL cache
            keys_to_remove = [key for key in self.url_cache.keys() if file_path in key]
            for key in keys_to_remove:
                del self.url_cache[key]
            
            # In a real CDN implementation, you would make API calls here
            # to invalidate the CDN cache. For now, we'll just log it.
            self.logger.info(f"CDN cache invalidation requested for: {file_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"CDN cache invalidation failed: {str(e)}")
            return False
    
    def preload_media(self, file_paths: List[str], priority: str = "normal") -> Dict[str, bool]:
        """Preload media files to CDN cache.
        
        Args:
            file_paths: List of file paths to preload
            priority: Preload priority ('low', 'normal', 'high')
            
        Returns:
            Dictionary mapping file paths to preload success status
        """
        try:
            preload_results = {}
            
            for file_path in file_paths:
                try:
                    # Generate CDN URLs to trigger caching
                    self.get_media_url(file_path, optimization='preview')
                    self.get_thumbnail_url(file_path, size='300x300')
                    
                    preload_results[file_path] = True
                    self.logger.debug(f"Preloaded media to CDN: {file_path}")
                    
                except Exception as e:
                    self.logger.warning(f"Failed to preload {file_path}: {str(e)}")
                    preload_results[file_path] = False
            
            successful_preloads = sum(1 for success in preload_results.values() if success)
            self.logger.info(f"Preloaded {successful_preloads}/{len(file_paths)} media files")
            
            return preload_results
            
        except Exception as e:
            self.logger.error(f"Media preloading failed: {str(e)}")
            return {path: False for path in file_paths}
    
    def get_cache_headers(self, file_type: str = 'media') -> Dict[str, str]:
        """Get appropriate cache headers for different file types.
        
        Args:
            file_type: Type of file ('media', 'thumbnail', 'metadata')
            
        Returns:
            Dictionary of cache headers
        """
        try:
            headers = {}
            
            # Determine max age based on file type
            if file_type == 'thumbnail':
                max_age = self.config.thumbnail_max_age
            elif file_type == 'metadata':
                max_age = self.config.metadata_max_age
            else:
                max_age = self.config.cache_control_max_age
            
            # Set cache control headers
            headers['Cache-Control'] = f'public, max-age={max_age}, immutable'
            headers['Expires'] = (datetime.utcnow() + timedelta(seconds=max_age)).strftime(
                '%a, %d %b %Y %H:%M:%S GMT'
            )
            
            # Add ETag for cache validation
            headers['ETag'] = f'"{int(time.time())}"'
            
            # Add Vary header for content negotiation
            headers['Vary'] = 'Accept, Accept-Encoding'
            
            return headers
            
        except Exception as e:
            self.logger.error(f"Failed to generate cache headers: {str(e)}")
            return {}
    
    def optimize_delivery(self, request_headers: Dict[str, str]) -> Dict[str, Any]:
        """Optimize delivery based on client capabilities.
        
        Args:
            request_headers: Client request headers
            
        Returns:
            Dictionary with optimization recommendations
        """
        try:
            optimizations = {
                'format': 'jpeg',
                'quality': 90,
                'progressive': True,
                'compression': True,
                'webp_supported': False,
                'avif_supported': False
            }
            
            # Check Accept header for format support
            accept_header = request_headers.get('Accept', '').lower()
            
            if 'image/webp' in accept_header:
                optimizations['webp_supported'] = True
                if self.config.enable_webp:
                    optimizations['format'] = 'webp'
            
            if 'image/avif' in accept_header:
                optimizations['avif_supported'] = True
                optimizations['format'] = 'avif'  # AVIF has better compression
            
            # Check connection speed hints
            save_data = request_headers.get('Save-Data', '').lower() == 'on'
            if save_data:
                optimizations['quality'] = 75
                optimizations['compression'] = True
            
            # Check device pixel ratio
            dpr = request_headers.get('DPR', '1')
            try:
                device_pixel_ratio = float(dpr)
                if device_pixel_ratio > 2:
                    optimizations['quality'] = min(95, optimizations['quality'] + 5)
            except ValueError:
                pass
            
            return optimizations
            
        except Exception as e:
            self.logger.error(f"Delivery optimization failed: {str(e)}")
            return {'format': 'jpeg', 'quality': 90}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get CDN performance statistics.
        
        Returns:
            Dictionary containing performance statistics
        """
        try:
            total_requests = self.stats.cache_hits + self.stats.cache_misses
            hit_rate = (self.stats.cache_hits / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'cdn_enabled': self.config.enabled,
                'total_requests': total_requests,
                'cache_hits': self.stats.cache_hits,
                'cache_misses': self.stats.cache_misses,
                'hit_rate_percent': hit_rate,
                'bytes_served': self.stats.bytes_served,
                'bytes_served_mb': self.stats.bytes_served / 1024 / 1024,
                'bandwidth_saved': self.stats.bandwidth_saved,
                'bandwidth_saved_mb': self.stats.bandwidth_saved / 1024 / 1024,
                'average_response_time_ms': self.stats.average_response_time,
                'url_cache_entries': len(self.url_cache),
                'config': {
                    'base_url': self.config.base_url,
                    'cache_max_age': self.config.cache_control_max_age,
                    'thumbnail_max_age': self.config.thumbnail_max_age,
                    'compression_enabled': self.config.enable_compression,
                    'webp_enabled': self.config.enable_webp
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get performance stats: {str(e)}")
            return {'error': str(e)}
    
    def _load_config_from_app(self) -> CDNConfig:
        """Load CDN configuration from Flask app config."""
        try:
            app_config = current_app.config
            
            return CDNConfig(
                enabled=app_config.get('CDN_ENABLED', False),
                base_url=app_config.get('CDN_BASE_URL', ''),
                cache_control_max_age=app_config.get('CDN_CACHE_MAX_AGE', 86400),
                thumbnail_max_age=app_config.get('CDN_THUMBNAIL_MAX_AGE', 2592000),
                metadata_max_age=app_config.get('CDN_METADATA_MAX_AGE', 3600),
                enable_compression=app_config.get('CDN_ENABLE_COMPRESSION', True),
                enable_webp=app_config.get('CDN_ENABLE_WEBP', True),
                enable_progressive_jpeg=app_config.get('CDN_ENABLE_PROGRESSIVE_JPEG', True),
                quality_levels=app_config.get('CDN_QUALITY_LEVELS', {
                    'thumbnail': 85,
                    'medium': 90,
                    'high': 95
                })
            )
            
        except Exception as e:
            self.logger.warning(f"Failed to load CDN config from app: {str(e)}")
            return CDNConfig()  # Return default config
    
    def _generate_cdn_url(self, file_path: str, optimization: Optional[str],
                         format_hint: Optional[str], cache_bust: bool) -> str:
        """Generate CDN URL with optimization parameters."""
        try:
            base_url = self.config.base_url.rstrip('/')
            
            # Extract file info
            file_name = os.path.basename(file_path)
            file_base, file_ext = os.path.splitext(file_name)
            
            # Determine output format
            output_format = self._determine_output_format(format_hint, file_ext)
            
            # Build CDN path
            cdn_path = f"/media/{file_base}.{output_format}"
            
            # Add optimization parameters
            params = []
            
            if optimization and optimization in self.quality_presets:
                preset = self.quality_presets[optimization]
                params.append(f"quality={preset['quality']}")
                if preset.get('progressive') and output_format == 'jpg':
                    params.append("progressive=true")
                if preset.get('optimize'):
                    params.append("optimize=true")
            
            if cache_bust:
                params.append(f"v={int(time.time())}")
            
            # Build final URL
            query_string = "&".join(params) if params else ""
            cdn_url = f"{base_url}{cdn_path}"
            if query_string:
                cdn_url += f"?{query_string}"
            
            return cdn_url
            
        except Exception as e:
            self.logger.error(f"CDN URL generation failed: {str(e)}")
            return self._get_local_url(file_path)
    
    def _determine_output_format(self, format_hint: Optional[str], original_ext: str) -> str:
        """Determine optimal output format."""
        try:
            # Remove leading dot from extension
            original_ext = original_ext.lstrip('.')
            
            # If format hint provided and supported, use it
            if format_hint:
                format_hint = format_hint.lower()
                if format_hint in ['webp', 'jpeg', 'jpg', 'png']:
                    return 'jpg' if format_hint == 'jpeg' else format_hint
            
            # Check if client supports WebP
            if hasattr(request, 'headers') and self.config.enable_webp:
                accept_header = request.headers.get('Accept', '').lower()
                if 'image/webp' in accept_header:
                    return 'webp'
            
            # Default format mapping
            format_mapping = {
                'jpeg': 'jpg',
                'jpg': 'jpg',
                'png': 'png',
                'webp': 'webp',
                'gif': 'gif'
            }
            
            return format_mapping.get(original_ext.lower(), 'jpg')
            
        except Exception as e:
            self.logger.debug(f"Format determination failed: {str(e)}")
            return 'jpg'
    
    def _get_local_url(self, file_path: str) -> str:
        """Get local URL for file when CDN is disabled."""
        try:
            # Ensure file path starts with /uploads/
            if not file_path.startswith('/uploads/'):
                if file_path.startswith('uploads/'):
                    file_path = '/' + file_path
                else:
                    file_path = '/uploads/' + file_path.lstrip('/')
            
            return file_path
            
        except Exception as e:
            self.logger.error(f"Local URL generation failed: {str(e)}")
            return file_path
    
    def _get_local_thumbnail_url(self, file_path: str, size: str) -> str:
        """Get local thumbnail URL."""
        try:
            # Extract filename and create thumbnail path
            file_name = os.path.basename(file_path)
            file_base, file_ext = os.path.splitext(file_name)
            
            thumbnail_filename = f"{file_base}_thumb_{size}.jpg"
            return f"/uploads/thumbnails/{thumbnail_filename}"
            
        except Exception as e:
            self.logger.error(f"Local thumbnail URL generation failed: {str(e)}")
            return file_path
    
    def _cleanup_url_cache(self) -> None:
        """Clean up old entries from URL cache."""
        try:
            now = datetime.now()
            keys_to_remove = []
            
            for key, (url, cached_time) in self.url_cache.items():
                if now - cached_time > self.url_cache_ttl:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.url_cache[key]
            
            if keys_to_remove:
                self.logger.debug(f"Cleaned up {len(keys_to_remove)} expired URL cache entries")
                
        except Exception as e:
            self.logger.error(f"URL cache cleanup failed: {str(e)}")


# Global CDN service instance
_cdn_service: Optional[CDNService] = None


def get_cdn_service() -> CDNService:
    """Get the global CDN service instance.
    
    Returns:
        CDNService instance
    """
    global _cdn_service
    if _cdn_service is None:
        _cdn_service = CDNService()
    return _cdn_service


def configure_cdn_service(config: CDNConfig) -> None:
    """Configure the global CDN service.
    
    Args:
        config: CDN configuration
    """
    global _cdn_service
    _cdn_service = CDNService(config)