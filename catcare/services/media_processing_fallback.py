"""
Media Processing Fallback and Error Handling Service.

This service provides comprehensive error handling and fallback mechanisms
for all media processing operations, ensuring graceful degradation when
processing steps fail.
"""

import os
import logging
import traceback
from typing import Optional, Dict, Any, List, Tuple, Union
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from PIL import Image

from catcare.services.storage_service import StorageService


class ProcessingErrorType(Enum):
    """Enumeration of processing error types."""
    COMPRESSION_FAILED = "compression_failed"
    EXIF_EXTRACTION_FAILED = "exif_extraction_failed"
    ROTATION_FAILED = "rotation_failed"
    THUMBNAIL_GENERATION_FAILED = "thumbnail_generation_failed"
    FORMAT_CONVERSION_FAILED = "format_conversion_failed"
    FILE_NOT_FOUND = "file_not_found"
    INVALID_FORMAT = "invalid_format"
    INSUFFICIENT_MEMORY = "insufficient_memory"
    PROCESSING_TIMEOUT = "processing_timeout"
    STORAGE_FAILED = "storage_failed"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ProcessingError:
    """Data class for processing error information."""
    error_type: ProcessingErrorType
    error_message: str
    original_exception: Optional[Exception]
    file_path: str
    processing_step: str
    timestamp: datetime
    user_message: str
    suggested_action: str
    is_recoverable: bool
    fallback_applied: bool


@dataclass
class FallbackResult:
    """Data class for fallback operation results."""
    success: bool
    fallback_type: str
    original_file: str
    fallback_file: Optional[str]
    error_message: Optional[str]
    user_message: str


class MediaProcessingFallback:
    """
    Comprehensive fallback and error handling for media processing operations.
    
    This class provides graceful error recovery, user-friendly error messages,
    and automatic fallback mechanisms for all media processing steps.
    """
    
    def __init__(self, storage_service: Optional[StorageService] = None):
        """Initialize the fallback handler.
        
        Args:
            storage_service: Optional storage service for file operations
        """
        self.logger = logging.getLogger(__name__)
        self.storage_service = storage_service
        
        # Error message templates for user-friendly messages
        self.error_messages = {
            ProcessingErrorType.COMPRESSION_FAILED: {
                'user_message': 'Image compression failed, but your original image has been saved.',
                'suggested_action': 'Try uploading a smaller image or different format.',
                'is_recoverable': True
            },
            ProcessingErrorType.EXIF_EXTRACTION_FAILED: {
                'user_message': 'Could not extract photo details, but your image has been saved.',
                'suggested_action': 'Location and camera information may not be available.',
                'is_recoverable': True
            },
            ProcessingErrorType.ROTATION_FAILED: {
                'user_message': 'Auto-rotation failed, but your image has been saved.',
                'suggested_action': 'You may need to manually rotate the image if needed.',
                'is_recoverable': True
            },
            ProcessingErrorType.THUMBNAIL_GENERATION_FAILED: {
                'user_message': 'Thumbnail creation failed, but your full image has been saved.',
                'suggested_action': 'Thumbnails will be generated later or use a placeholder.',
                'is_recoverable': True
            },
            ProcessingErrorType.FORMAT_CONVERSION_FAILED: {
                'user_message': 'Format conversion failed, using original format.',
                'suggested_action': 'Try converting the image to JPEG before uploading.',
                'is_recoverable': True
            },
            ProcessingErrorType.FILE_NOT_FOUND: {
                'user_message': 'The uploaded file could not be found.',
                'suggested_action': 'Please try uploading the file again.',
                'is_recoverable': False
            },
            ProcessingErrorType.INVALID_FORMAT: {
                'user_message': 'This file format is not supported.',
                'suggested_action': 'Please upload a JPEG, PNG, or other supported image format.',
                'is_recoverable': False
            },
            ProcessingErrorType.INSUFFICIENT_MEMORY: {
                'user_message': 'The image is too large to process.',
                'suggested_action': 'Try uploading a smaller image or reduce the image size.',
                'is_recoverable': False
            },
            ProcessingErrorType.PROCESSING_TIMEOUT: {
                'user_message': 'Image processing took too long and was cancelled.',
                'suggested_action': 'Try uploading a smaller image or try again later.',
                'is_recoverable': True
            },
            ProcessingErrorType.STORAGE_FAILED: {
                'user_message': 'Failed to save the processed image.',
                'suggested_action': 'Please try uploading again or contact support.',
                'is_recoverable': True
            },
            ProcessingErrorType.UNKNOWN_ERROR: {
                'user_message': 'An unexpected error occurred during processing.',
                'suggested_action': 'Please try again or contact support if the problem persists.',
                'is_recoverable': True
            }
        }
        
        # Supported image formats for fallback operations
        self.supported_formats = {'JPEG', 'PNG', 'WEBP', 'TIFF', 'BMP'}
        
        # Maximum file size for processing (50MB)
        self.max_file_size = 50 * 1024 * 1024
        
        # Processing timeout (30 seconds)
        self.processing_timeout = 30
    
    def handle_processing_failure(self, file_path: str, error: Exception, 
                                processing_step: str, **kwargs) -> FallbackResult:
        """
        Handle processing failure with appropriate fallback mechanism.
        
        Args:
            file_path: Path to the file being processed
            error: The exception that occurred
            processing_step: Name of the processing step that failed
            **kwargs: Additional context information
            
        Returns:
            FallbackResult with fallback operation details
        """
        try:
            # Classify the error type
            error_type = self._classify_error(error, file_path, processing_step)
            
            # Create processing error record
            processing_error = ProcessingError(
                error_type=error_type,
                error_message=str(error),
                original_exception=error,
                file_path=file_path,
                processing_step=processing_step,
                timestamp=datetime.now(),
                user_message=self.error_messages[error_type]['user_message'],
                suggested_action=self.error_messages[error_type]['suggested_action'],
                is_recoverable=self.error_messages[error_type]['is_recoverable'],
                fallback_applied=False
            )
            
            # Log the error for administrators
            self._log_processing_error(processing_error)
            
            # Apply appropriate fallback mechanism
            fallback_result = self._apply_fallback(processing_error, **kwargs)
            
            # Update error record with fallback status
            processing_error.fallback_applied = fallback_result.success
            
            return fallback_result
            
        except Exception as fallback_error:
            self.logger.error(f"Fallback handling failed: {str(fallback_error)}")
            return FallbackResult(
                success=False,
                fallback_type="emergency_fallback",
                original_file=file_path,
                fallback_file=None,
                error_message=str(fallback_error),
                user_message="Processing failed and recovery was not possible. Please try again."
            )
    
    def handle_compression_failure(self, file_path: str, error: Exception, 
                                 target_quality: int = 85) -> FallbackResult:
        """
        Handle image compression failure with fallback options.
        
        Args:
            file_path: Path to the image file
            error: The compression error
            target_quality: Target compression quality
            
        Returns:
            FallbackResult with compression fallback details
        """
        try:
            self.logger.warning(f"Compression failed for {file_path}: {str(error)}")
            
            # Try progressive fallback strategies
            fallback_strategies = [
                ('lower_quality', lambda: self._try_lower_quality_compression(file_path, target_quality - 20)),
                ('basic_compression', lambda: self._try_basic_compression(file_path)),
                ('format_conversion', lambda: self._try_format_conversion_compression(file_path)),
                ('use_original', lambda: self._use_original_file(file_path))
            ]
            
            for strategy_name, strategy_func in fallback_strategies:
                try:
                    result = strategy_func()
                    if result.success:
                        self.logger.info(f"Compression fallback successful using {strategy_name}")
                        return result
                except Exception as strategy_error:
                    self.logger.debug(f"Compression fallback {strategy_name} failed: {str(strategy_error)}")
                    continue
            
            # All fallback strategies failed
            return FallbackResult(
                success=False,
                fallback_type="compression_fallback_failed",
                original_file=file_path,
                fallback_file=None,
                error_message="All compression fallback strategies failed",
                user_message="Image compression failed. The original image will be used."
            )
            
        except Exception as e:
            self.logger.error(f"Compression fallback handling failed: {str(e)}")
            return self._emergency_fallback(file_path, "compression_fallback_error")
    
    def handle_exif_extraction_failure(self, file_path: str, error: Exception) -> FallbackResult:
        """
        Handle EXIF extraction failure with fallback metadata.
        
        Args:
            file_path: Path to the image file
            error: The EXIF extraction error
            
        Returns:
            FallbackResult with EXIF fallback details
        """
        try:
            self.logger.warning(f"EXIF extraction failed for {file_path}: {str(error)}")
            
            # Create fallback metadata using file system information
            fallback_metadata = self._create_fallback_metadata(file_path)
            
            return FallbackResult(
                success=True,
                fallback_type="exif_fallback_metadata",
                original_file=file_path,
                fallback_file=file_path,  # Same file, different metadata
                error_message=None,
                user_message="Photo details extracted from file information instead of camera data."
            )
            
        except Exception as e:
            self.logger.error(f"EXIF fallback handling failed: {str(e)}")
            return self._emergency_fallback(file_path, "exif_fallback_error")
    
    def handle_rotation_failure(self, file_path: str, error: Exception, 
                              orientation: int = 1) -> FallbackResult:
        """
        Handle image rotation failure with fallback options.
        
        Args:
            file_path: Path to the image file
            error: The rotation error
            orientation: EXIF orientation value
            
        Returns:
            FallbackResult with rotation fallback details
        """
        try:
            self.logger.warning(f"Rotation failed for {file_path}: {str(error)}")
            
            # Try alternative rotation methods
            fallback_strategies = [
                ('simple_rotation', lambda: self._try_simple_rotation(file_path, orientation)),
                ('manual_rotation_hint', lambda: self._provide_manual_rotation_hint(file_path, orientation)),
                ('use_original', lambda: self._use_original_file(file_path))
            ]
            
            for strategy_name, strategy_func in fallback_strategies:
                try:
                    result = strategy_func()
                    if result.success:
                        self.logger.info(f"Rotation fallback successful using {strategy_name}")
                        return result
                except Exception as strategy_error:
                    self.logger.debug(f"Rotation fallback {strategy_name} failed: {str(strategy_error)}")
                    continue
            
            # All fallback strategies failed
            return FallbackResult(
                success=False,
                fallback_type="rotation_fallback_failed",
                original_file=file_path,
                fallback_file=None,
                error_message="All rotation fallback strategies failed",
                user_message="Auto-rotation failed. You may need to manually rotate the image."
            )
            
        except Exception as e:
            self.logger.error(f"Rotation fallback handling failed: {str(e)}")
            return self._emergency_fallback(file_path, "rotation_fallback_error")
    
    def handle_thumbnail_failure(self, file_path: str, error: Exception, 
                               sizes: List[Tuple[int, int]] = None) -> FallbackResult:
        """
        Handle thumbnail generation failure with placeholder creation.
        
        Args:
            file_path: Path to the image file
            error: The thumbnail generation error
            sizes: List of thumbnail sizes that failed
            
        Returns:
            FallbackResult with thumbnail fallback details
        """
        try:
            self.logger.warning(f"Thumbnail generation failed for {file_path}: {str(error)}")
            
            sizes = sizes or [(150, 150), (300, 300), (600, 400)]
            
            # Try to create placeholder thumbnails
            placeholder_result = self._create_placeholder_thumbnails(file_path, sizes)
            
            if placeholder_result.success:
                return placeholder_result
            
            # If placeholder creation fails, use original image as thumbnail
            return FallbackResult(
                success=True,
                fallback_type="original_as_thumbnail",
                original_file=file_path,
                fallback_file=file_path,
                error_message=None,
                user_message="Thumbnails will be generated later. Using full image for now."
            )
            
        except Exception as e:
            self.logger.error(f"Thumbnail fallback handling failed: {str(e)}")
            return self._emergency_fallback(file_path, "thumbnail_fallback_error")
    
    def handle_format_conversion_failure(self, file_path: str, error: Exception, 
                                       target_format: str = 'JPEG') -> FallbackResult:
        """
        Handle format conversion failure with alternative approaches.
        
        Args:
            file_path: Path to the image file
            error: The format conversion error
            target_format: Target format that failed
            
        Returns:
            FallbackResult with format conversion fallback details
        """
        try:
            self.logger.warning(f"Format conversion to {target_format} failed for {file_path}: {str(error)}")
            
            # Try alternative conversion strategies
            fallback_strategies = [
                ('alternative_format', lambda: self._try_alternative_format_conversion(file_path)),
                ('basic_conversion', lambda: self._try_basic_format_conversion(file_path, target_format)),
                ('use_original', lambda: self._use_original_file(file_path))
            ]
            
            for strategy_name, strategy_func in fallback_strategies:
                try:
                    result = strategy_func()
                    if result.success:
                        self.logger.info(f"Format conversion fallback successful using {strategy_name}")
                        return result
                except Exception as strategy_error:
                    self.logger.debug(f"Format conversion fallback {strategy_name} failed: {str(strategy_error)}")
                    continue
            
            # All fallback strategies failed
            return FallbackResult(
                success=False,
                fallback_type="format_conversion_fallback_failed",
                original_file=file_path,
                fallback_file=None,
                error_message="All format conversion fallback strategies failed",
                user_message="Format conversion failed. The original format will be used."
            )
            
        except Exception as e:
            self.logger.error(f"Format conversion fallback handling failed: {str(e)}")
            return self._emergency_fallback(file_path, "format_conversion_fallback_error")
    
    def _classify_error(self, error: Exception, file_path: str, processing_step: str) -> ProcessingErrorType:
        """
        Classify an error into a specific error type.
        
        Args:
            error: The exception that occurred
            file_path: Path to the file being processed
            processing_step: Name of the processing step
            
        Returns:
            ProcessingErrorType enum value
        """
        error_str = str(error).lower()
        error_type_name = type(error).__name__.lower()
        
        # File-related errors
        if not os.path.exists(file_path):
            return ProcessingErrorType.FILE_NOT_FOUND
        
        if 'filenotfounderror' in error_type_name or 'no such file' in error_str:
            return ProcessingErrorType.FILE_NOT_FOUND
        
        # Memory-related errors
        if 'memoryerror' in error_type_name or 'out of memory' in error_str or 'memory' in error_str:
            return ProcessingErrorType.INSUFFICIENT_MEMORY
        
        # Timeout errors
        if 'timeout' in error_str or 'timeouterror' in error_type_name:
            return ProcessingErrorType.PROCESSING_TIMEOUT
        
        # Format-related errors
        if 'cannot identify image file' in error_str or 'unsupported format' in error_str:
            return ProcessingErrorType.INVALID_FORMAT
        
        # Step-specific error classification
        if 'compression' in processing_step.lower():
            return ProcessingErrorType.COMPRESSION_FAILED
        elif 'exif' in processing_step.lower() or 'metadata' in processing_step.lower():
            return ProcessingErrorType.EXIF_EXTRACTION_FAILED
        elif 'rotation' in processing_step.lower() or 'orient' in processing_step.lower():
            return ProcessingErrorType.ROTATION_FAILED
        elif 'thumbnail' in processing_step.lower():
            return ProcessingErrorType.THUMBNAIL_GENERATION_FAILED
        elif 'conversion' in processing_step.lower() or 'format' in processing_step.lower():
            return ProcessingErrorType.FORMAT_CONVERSION_FAILED
        elif 'storage' in processing_step.lower() or 'save' in processing_step.lower():
            return ProcessingErrorType.STORAGE_FAILED
        
        # Default to unknown error
        return ProcessingErrorType.UNKNOWN_ERROR
    
    def _apply_fallback(self, processing_error: ProcessingError, **kwargs) -> FallbackResult:
        """
        Apply appropriate fallback mechanism based on error type.
        
        Args:
            processing_error: The processing error information
            **kwargs: Additional context for fallback operations
            
        Returns:
            FallbackResult with fallback operation details
        """
        error_type = processing_error.error_type
        file_path = processing_error.file_path
        
        # Route to specific fallback handlers
        if error_type == ProcessingErrorType.COMPRESSION_FAILED:
            return self.handle_compression_failure(file_path, processing_error.original_exception)
        elif error_type == ProcessingErrorType.EXIF_EXTRACTION_FAILED:
            return self.handle_exif_extraction_failure(file_path, processing_error.original_exception)
        elif error_type == ProcessingErrorType.ROTATION_FAILED:
            orientation = kwargs.get('orientation', 1)
            return self.handle_rotation_failure(file_path, processing_error.original_exception, orientation)
        elif error_type == ProcessingErrorType.THUMBNAIL_GENERATION_FAILED:
            sizes = kwargs.get('sizes')
            return self.handle_thumbnail_failure(file_path, processing_error.original_exception, sizes)
        elif error_type == ProcessingErrorType.FORMAT_CONVERSION_FAILED:
            target_format = kwargs.get('target_format', 'JPEG')
            return self.handle_format_conversion_failure(file_path, processing_error.original_exception, target_format)
        elif error_type in [ProcessingErrorType.FILE_NOT_FOUND, ProcessingErrorType.INVALID_FORMAT]:
            # Non-recoverable errors
            return FallbackResult(
                success=False,
                fallback_type="non_recoverable",
                original_file=file_path,
                fallback_file=None,
                error_message=processing_error.error_message,
                user_message=processing_error.user_message
            )
        else:
            # Generic fallback - use original file
            return self._use_original_file(file_path)
    
    def _log_processing_error(self, processing_error: ProcessingError):
        """
        Log processing error for system administrators.
        
        Args:
            processing_error: The processing error to log
        """
        try:
            # Create detailed error log entry
            error_details = {
                'timestamp': processing_error.timestamp.isoformat(),
                'error_type': processing_error.error_type.value,
                'processing_step': processing_error.processing_step,
                'file_path': processing_error.file_path,
                'error_message': processing_error.error_message,
                'is_recoverable': processing_error.is_recoverable,
                'fallback_applied': processing_error.fallback_applied
            }
            
            # Log with appropriate level based on error severity
            if processing_error.is_recoverable:
                self.logger.warning(f"Recoverable processing error: {error_details}")
            else:
                self.logger.error(f"Non-recoverable processing error: {error_details}")
            
            # Log stack trace for debugging if original exception exists
            if processing_error.original_exception:
                self.logger.debug(f"Original exception traceback: {traceback.format_exception(type(processing_error.original_exception), processing_error.original_exception, processing_error.original_exception.__traceback__)}")
            
        except Exception as log_error:
            self.logger.error(f"Failed to log processing error: {str(log_error)}")
    
    def _try_lower_quality_compression(self, file_path: str, quality: int) -> FallbackResult:
        """Try compression with lower quality settings."""
        try:
            if quality < 30:  # Don't go too low
                raise ValueError("Quality too low for acceptable results")
            
            output_path = self._get_fallback_filename(file_path, "compressed_low")
            
            with Image.open(file_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                img.save(output_path, format='JPEG', quality=quality, optimize=True)
            
            return FallbackResult(
                success=True,
                fallback_type="lower_quality_compression",
                original_file=file_path,
                fallback_file=output_path,
                error_message=None,
                user_message=f"Image compressed with reduced quality ({quality}%) to ensure successful processing."
            )
            
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_type="lower_quality_compression_failed",
                original_file=file_path,
                fallback_file=None,
                error_message=str(e),
                user_message="Lower quality compression failed."
            )
    
    def _try_basic_compression(self, file_path: str) -> FallbackResult:
        """Try basic compression without advanced features."""
        try:
            output_path = self._get_fallback_filename(file_path, "basic_compressed")
            
            with Image.open(file_path) as img:
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Basic compression without optimization
                img.save(output_path, format='JPEG', quality=75)
            
            return FallbackResult(
                success=True,
                fallback_type="basic_compression",
                original_file=file_path,
                fallback_file=output_path,
                error_message=None,
                user_message="Image compressed using basic settings."
            )
            
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_type="basic_compression_failed",
                original_file=file_path,
                fallback_file=None,
                error_message=str(e),
                user_message="Basic compression failed."
            )
    
    def _try_format_conversion_compression(self, file_path: str) -> FallbackResult:
        """Try compression after format conversion."""
        try:
            # First convert to a standard format, then compress
            temp_path = self._get_fallback_filename(file_path, "temp_converted")
            output_path = self._get_fallback_filename(file_path, "converted_compressed")
            
            with Image.open(file_path) as img:
                # Convert to RGB
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPEG first
                img.save(temp_path, format='JPEG', quality=95)
            
            # Now try to compress the converted image
            with Image.open(temp_path) as img:
                img.save(output_path, format='JPEG', quality=80, optimize=True)
            
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            return FallbackResult(
                success=True,
                fallback_type="format_conversion_compression",
                original_file=file_path,
                fallback_file=output_path,
                error_message=None,
                user_message="Image converted to JPEG format and compressed."
            )
            
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_type="format_conversion_compression_failed",
                original_file=file_path,
                fallback_file=None,
                error_message=str(e),
                user_message="Format conversion compression failed."
            )
    
    def _use_original_file(self, file_path: str) -> FallbackResult:
        """Use the original file without processing."""
        return FallbackResult(
            success=True,
            fallback_type="use_original",
            original_file=file_path,
            fallback_file=file_path,
            error_message=None,
            user_message="Using original file without processing."
        )
    
    def _create_fallback_metadata(self, file_path: str) -> Dict[str, Any]:
        """Create fallback metadata from file system information."""
        try:
            stat_info = os.stat(file_path)
            
            # Get basic image information
            with Image.open(file_path) as img:
                width, height = img.size
                format_type = img.format
            
            fallback_metadata = {
                'timestamp_processed': datetime.now(),
                'file_size': stat_info.st_size,
                'image_dimensions': (width, height),
                'format': format_type,
                'fallback_metadata': True,
                'metadata_source': 'file_system'
            }
            
            return fallback_metadata
            
        except Exception as e:
            self.logger.warning(f"Failed to create fallback metadata: {str(e)}")
            return {
                'timestamp_processed': datetime.now(),
                'fallback_metadata': True,
                'metadata_source': 'minimal',
                'error': str(e)
            }
    
    def _try_simple_rotation(self, file_path: str, orientation: int) -> FallbackResult:
        """Try simple rotation without advanced features."""
        try:
            if orientation == 1:  # No rotation needed
                return self._use_original_file(file_path)
            
            output_path = self._get_fallback_filename(file_path, "rotated")
            
            with Image.open(file_path) as img:
                # Simple rotation mapping
                rotation_map = {
                    3: 180,  # Rotate 180 degrees
                    6: 270,  # Rotate 90 degrees clockwise (270 counter-clockwise)
                    8: 90    # Rotate 90 degrees counter-clockwise
                }
                
                if orientation in rotation_map:
                    rotated_img = img.rotate(rotation_map[orientation], expand=True)
                    rotated_img.save(output_path, format=img.format, quality=95)
                    
                    return FallbackResult(
                        success=True,
                        fallback_type="simple_rotation",
                        original_file=file_path,
                        fallback_file=output_path,
                        error_message=None,
                        user_message="Image rotated using basic rotation."
                    )
                else:
                    return self._use_original_file(file_path)
            
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_type="simple_rotation_failed",
                original_file=file_path,
                fallback_file=None,
                error_message=str(e),
                user_message="Simple rotation failed."
            )
    
    def _provide_manual_rotation_hint(self, file_path: str, orientation: int) -> FallbackResult:
        """Provide manual rotation hint to user."""
        rotation_hints = {
            3: "Image appears upside down. You may need to rotate it 180 degrees.",
            6: "Image appears rotated. You may need to rotate it 90 degrees clockwise.",
            8: "Image appears rotated. You may need to rotate it 90 degrees counter-clockwise."
        }
        
        hint = rotation_hints.get(orientation, "Image orientation may need manual adjustment.")
        
        return FallbackResult(
            success=True,
            fallback_type="manual_rotation_hint",
            original_file=file_path,
            fallback_file=file_path,
            error_message=None,
            user_message=hint
        )
    
    def _create_placeholder_thumbnails(self, file_path: str, sizes: List[Tuple[int, int]]) -> FallbackResult:
        """Create placeholder thumbnails when generation fails."""
        try:
            placeholder_files = []
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            output_dir = os.path.dirname(file_path)
            
            for width, height in sizes:
                placeholder_path = os.path.join(output_dir, f"{base_name}_placeholder_{width}x{height}.jpg")
                
                # Create a simple placeholder image
                placeholder_img = Image.new('RGB', (width, height), color=(200, 200, 200))
                placeholder_img.save(placeholder_path, format='JPEG', quality=80)
                placeholder_files.append(placeholder_path)
            
            return FallbackResult(
                success=True,
                fallback_type="placeholder_thumbnails",
                original_file=file_path,
                fallback_file=placeholder_files[0] if placeholder_files else None,
                error_message=None,
                user_message="Placeholder thumbnails created. Full image thumbnails will be generated later."
            )
            
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_type="placeholder_thumbnails_failed",
                original_file=file_path,
                fallback_file=None,
                error_message=str(e),
                user_message="Could not create placeholder thumbnails."
            )
    
    def _try_alternative_format_conversion(self, file_path: str) -> FallbackResult:
        """Try alternative format conversion approaches."""
        try:
            # Try converting to PNG instead of JPEG
            output_path = self._get_fallback_filename(file_path, "converted_png")
            
            with Image.open(file_path) as img:
                img.save(output_path, format='PNG')
            
            return FallbackResult(
                success=True,
                fallback_type="alternative_format_conversion",
                original_file=file_path,
                fallback_file=output_path,
                error_message=None,
                user_message="Image converted to PNG format instead."
            )
            
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_type="alternative_format_conversion_failed",
                original_file=file_path,
                fallback_file=None,
                error_message=str(e),
                user_message="Alternative format conversion failed."
            )
    
    def _try_basic_format_conversion(self, file_path: str, target_format: str) -> FallbackResult:
        """Try basic format conversion without advanced features."""
        try:
            output_path = self._get_fallback_filename(file_path, f"basic_{target_format.lower()}")
            
            with Image.open(file_path) as img:
                if target_format.upper() == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                img.save(output_path, format=target_format.upper())
            
            return FallbackResult(
                success=True,
                fallback_type="basic_format_conversion",
                original_file=file_path,
                fallback_file=output_path,
                error_message=None,
                user_message=f"Image converted to {target_format} using basic conversion."
            )
            
        except Exception as e:
            return FallbackResult(
                success=False,
                fallback_type="basic_format_conversion_failed",
                original_file=file_path,
                fallback_file=None,
                error_message=str(e),
                user_message="Basic format conversion failed."
            )
    
    def _emergency_fallback(self, file_path: str, fallback_type: str) -> FallbackResult:
        """Emergency fallback when all other fallbacks fail."""
        return FallbackResult(
            success=True,
            fallback_type=fallback_type,
            original_file=file_path,
            fallback_file=file_path,
            error_message=None,
            user_message="Processing encountered issues but your file has been saved. Some features may not be available."
        )
    
    def _get_fallback_filename(self, original_path: str, suffix: str) -> str:
        """Generate a filename for fallback files."""
        directory = os.path.dirname(original_path)
        base_name = os.path.splitext(os.path.basename(original_path))[0]
        extension = os.path.splitext(original_path)[1]
        
        return os.path.join(directory, f"{base_name}_{suffix}{extension}")
    
    def get_user_friendly_error_message(self, error_type: ProcessingErrorType) -> str:
        """Get user-friendly error message for a specific error type."""
        return self.error_messages.get(error_type, self.error_messages[ProcessingErrorType.UNKNOWN_ERROR])['user_message']
    
    def get_suggested_action(self, error_type: ProcessingErrorType) -> str:
        """Get suggested action for a specific error type."""
        return self.error_messages.get(error_type, self.error_messages[ProcessingErrorType.UNKNOWN_ERROR])['suggested_action']
    
    def is_error_recoverable(self, error_type: ProcessingErrorType) -> bool:
        """Check if an error type is recoverable."""
        return self.error_messages.get(error_type, self.error_messages[ProcessingErrorType.UNKNOWN_ERROR])['is_recoverable']