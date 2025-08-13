"""
Media Processing Service for advanced image and video processing.

This service handles image compression, EXIF extraction, thumbnail generation,
format conversion, and other media processing operations.
"""

import os
import logging
import tempfile
import time
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from datetime import datetime
from PIL import Image, ExifTags, ImageOps, ImageFilter
from PIL.ExifTags import TAGS, GPSTAGS
import exifread
import magic

from catcare.services.storage_service import StorageService
from catcare.services.processing_monitor import ProcessingMonitor
from catcare.services.media_processing_fallback import MediaProcessingFallback, ProcessingErrorType
from catcare.services.media_cache_service import get_cache_service
from catcare.services.temp_file_manager import get_temp_file_manager
from catcare.services.cdn_service import get_cdn_service


@dataclass
class ProcessedMedia:
    """Data class for processed media information."""
    original_filename: str
    processed_filename: str
    file_size_original: int
    file_size_processed: int
    compression_ratio: float
    format_original: str
    format_processed: str
    thumbnails: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    processing_time: float
    processing_status: str


@dataclass
class MediaMetadata:
    """Data class for media metadata."""
    timestamp_original: Optional[datetime]
    timestamp_processed: datetime
    gps_coordinates: Optional[Tuple[float, float]]
    location_name: Optional[str]
    camera_info: Optional[Dict[str, str]]
    image_dimensions: Tuple[int, int]
    color_profile: Optional[str]
    orientation: int


@dataclass
class GPSCoordinates:
    """Data class for GPS coordinates."""
    latitude: float
    longitude: float
    altitude: Optional[float] = None


@dataclass
class CameraInfo:
    """Data class for camera information."""
    make: Optional[str] = None
    model: Optional[str] = None
    software: Optional[str] = None
    lens_make: Optional[str] = None
    lens_model: Optional[str] = None
    focal_length: Optional[str] = None
    aperture: Optional[str] = None
    iso: Optional[str] = None
    exposure_time: Optional[str] = None
    flash: Optional[str] = None


@dataclass
class ThumbnailInfo:
    """Data class for thumbnail information."""
    size_label: str  # e.g., "150x150", "300x300"
    filename: str
    file_size: int
    width: int
    height: int
    format: str = 'JPEG'


class EXIFExtractor:
    """Class for extracting and processing EXIF metadata from images."""
    
    def __init__(self):
        """Initialize the EXIF extractor."""
        self.logger = logging.getLogger(__name__)
        
        # Supported formats for EXIF extraction
        self.supported_formats = ['JPEG', 'TIFF', 'HEIC', 'HEIF']
        
        # GPS coordinate precision (decimal places)
        self.gps_precision = 6
        
        # Sensitive EXIF tags to strip for privacy
        self.sensitive_tags = {
            'GPS GPSProcessingMethod',
            'GPS GPSAreaInformation', 
            'GPS GPSDateStamp',
            'GPS GPSTimeStamp',
            'UserComment',
            'ImageUniqueID',
            'CameraOwnerName',
            'BodySerialNumber',
            'LensSerialNumber',
            'InternalSerialNumber'
        }
    
    def extract_exif_data(self, image_path: str) -> Dict[str, Any]:
        """Extract all EXIF data from an image file.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Dictionary containing extracted EXIF data
        """
        try:
            # Check if format supports EXIF
            format_type = self._detect_image_format(image_path)
            if format_type not in self.supported_formats:
                self.logger.debug(f"Format {format_type} does not support EXIF data")
                return {}
            
            exif_data = {}
            
            # Try PIL first for basic EXIF data
            try:
                with Image.open(image_path) as img:
                    pil_exif = img.getexif()
                    if pil_exif:
                        # Convert numeric tags to readable names
                        for tag_id, value in pil_exif.items():
                            tag_name = TAGS.get(tag_id, tag_id)
                            exif_data[tag_name] = value
                        
                        self.logger.debug(f"Extracted {len(exif_data)} EXIF tags using PIL")
            except Exception as e:
                self.logger.debug(f"PIL EXIF extraction failed: {str(e)}")
            
            # Try exifread for more detailed data
            try:
                with open(image_path, 'rb') as f:
                    exifread_tags = exifread.process_file(f, details=True)
                    
                    # Convert exifread tags to dictionary
                    for tag_name, tag_value in exifread_tags.items():
                        if not tag_name.startswith('JPEGThumbnail'):
                            try:
                                # Convert to string and clean up
                                str_value = str(tag_value).strip()
                                if str_value and str_value != 'None':
                                    exif_data[tag_name] = str_value
                            except Exception:
                                continue
                
                self.logger.debug(f"Enhanced with {len(exifread_tags)} tags using exifread")
            except Exception as e:
                self.logger.debug(f"exifread extraction failed: {str(e)}")
            
            # Clean sensitive data
            cleaned_data = self.clean_sensitive_data(exif_data)
            
            self.logger.info(f"Successfully extracted EXIF data from {image_path} "
                           f"({len(cleaned_data)} tags after cleaning)")
            
            return cleaned_data
            
        except Exception as e:
            self.logger.error(f"EXIF extraction failed for {image_path}: {str(e)}")
            return {}
    
    def get_gps_coordinates(self, exif_data: Dict[str, Any]) -> Optional[GPSCoordinates]:
        """Extract GPS coordinates from EXIF data.
        
        Args:
            exif_data: Dictionary containing EXIF data
            
        Returns:
            GPSCoordinates object or None if no GPS data found
        """
        try:
            # Try PIL format first
            gps_info = exif_data.get('GPSInfo')
            if gps_info:
                return self._parse_pil_gps(gps_info)
            
            # Try exifread format
            lat_ref = exif_data.get('GPS GPSLatitudeRef')
            lat_data = exif_data.get('GPS GPSLatitude')
            lon_ref = exif_data.get('GPS GPSLongitudeRef')
            lon_data = exif_data.get('GPS GPSLongitude')
            
            if all([lat_ref, lat_data, lon_ref, lon_data]):
                latitude = self._convert_gps_coordinate(lat_data, lat_ref)
                longitude = self._convert_gps_coordinate(lon_data, lon_ref)
                
                # Get altitude if available
                altitude = None
                alt_data = exif_data.get('GPS GPSAltitude')
                alt_ref = exif_data.get('GPS GPSAltitudeRef')
                if alt_data:
                    altitude = self._convert_gps_altitude(alt_data, alt_ref)
                
                coords = GPSCoordinates(
                    latitude=round(latitude, self.gps_precision),
                    longitude=round(longitude, self.gps_precision),
                    altitude=altitude
                )
                
                self.logger.debug(f"Extracted GPS coordinates: {coords.latitude}, {coords.longitude}")
                return coords
            
            return None
            
        except Exception as e:
            self.logger.warning(f"GPS coordinate extraction failed: {str(e)}")
            return None
    
    def get_timestamp(self, exif_data: Dict[str, Any]) -> Optional[datetime]:
        """Extract original timestamp from EXIF data.
        
        Args:
            exif_data: Dictionary containing EXIF data
            
        Returns:
            datetime object or None if no timestamp found
        """
        try:
            # Try different timestamp fields in order of preference
            timestamp_fields = [
                'DateTimeOriginal',
                'DateTime',
                'DateTimeDigitized',
                'EXIF DateTimeOriginal',
                'EXIF DateTime',
                'EXIF DateTimeDigitized'
            ]
            
            for field in timestamp_fields:
                timestamp_str = exif_data.get(field)
                if timestamp_str:
                    try:
                        # Parse EXIF datetime format: "YYYY:MM:DD HH:MM:SS"
                        timestamp_str = str(timestamp_str).strip()
                        if ':' in timestamp_str and len(timestamp_str) >= 19:
                            # Replace first two colons with dashes for proper parsing
                            parts = timestamp_str.split(' ')
                            if len(parts) >= 2:
                                date_part = parts[0].replace(':', '-', 2)
                                time_part = parts[1]
                                iso_format = f"{date_part} {time_part}"
                                
                                timestamp = datetime.strptime(iso_format, '%Y-%m-%d %H:%M:%S')
                                self.logger.debug(f"Extracted timestamp from {field}: {timestamp}")
                                return timestamp
                    except ValueError as e:
                        self.logger.debug(f"Could not parse timestamp from {field}: {timestamp_str} - {str(e)}")
                        continue
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Timestamp extraction failed: {str(e)}")
            return None
    
    def get_camera_info(self, exif_data: Dict[str, Any]) -> Optional[CameraInfo]:
        """Extract camera information from EXIF data.
        
        Args:
            exif_data: Dictionary containing EXIF data
            
        Returns:
            CameraInfo object or None if no camera info found
        """
        try:
            camera_info = CameraInfo()
            
            # Extract basic camera information
            camera_info.make = self._get_exif_value(exif_data, ['Make', 'Image Make'])
            camera_info.model = self._get_exif_value(exif_data, ['Model', 'Image Model'])
            camera_info.software = self._get_exif_value(exif_data, ['Software', 'Image Software'])
            
            # Extract lens information
            camera_info.lens_make = self._get_exif_value(exif_data, ['LensMake', 'EXIF LensMake'])
            camera_info.lens_model = self._get_exif_value(exif_data, ['LensModel', 'EXIF LensModel'])
            
            # Extract camera settings
            camera_info.focal_length = self._get_exif_value(exif_data, ['FocalLength', 'EXIF FocalLength'])
            camera_info.aperture = self._get_exif_value(exif_data, ['FNumber', 'EXIF FNumber', 'ApertureValue', 'EXIF ApertureValue'])
            camera_info.iso = self._get_exif_value(exif_data, ['ISOSpeedRatings', 'EXIF ISOSpeedRatings', 'ISO'])
            camera_info.exposure_time = self._get_exif_value(exif_data, ['ExposureTime', 'EXIF ExposureTime'])
            camera_info.flash = self._get_exif_value(exif_data, ['Flash', 'EXIF Flash'])
            
            # Check if we have any camera information
            if any([camera_info.make, camera_info.model, camera_info.software]):
                self.logger.debug(f"Extracted camera info: {camera_info.make} {camera_info.model}")
                return camera_info
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Camera info extraction failed: {str(e)}")
            return None
    
    def clean_sensitive_data(self, exif_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive EXIF data for privacy protection.
        
        Args:
            exif_data: Dictionary containing EXIF data
            
        Returns:
            Dictionary with sensitive data removed
        """
        try:
            cleaned_data = {}
            
            for key, value in exif_data.items():
                # Skip sensitive tags
                if any(sensitive in key for sensitive in self.sensitive_tags):
                    self.logger.debug(f"Removing sensitive EXIF tag: {key}")
                    continue
                
                # Skip binary data and thumbnails
                if isinstance(value, bytes) or 'Thumbnail' in key or 'thumbnail' in key:
                    continue
                
                # Skip very long values that might contain sensitive data
                if isinstance(value, str) and len(value) > 200:
                    continue
                
                cleaned_data[key] = value
            
            removed_count = len(exif_data) - len(cleaned_data)
            if removed_count > 0:
                self.logger.debug(f"Removed {removed_count} sensitive/binary EXIF tags")
            
            return cleaned_data
            
        except Exception as e:
            self.logger.warning(f"EXIF data cleaning failed: {str(e)}")
            return exif_data
    
    def _detect_image_format(self, image_path: str) -> str:
        """Detect image format using magic library.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Format string
        """
        try:
            mime_type = magic.from_file(image_path, mime=True)
            format_map = {
                'image/jpeg': 'JPEG',
                'image/tiff': 'TIFF',
                'image/heic': 'HEIC',
                'image/heif': 'HEIF'
            }
            return format_map.get(mime_type, 'UNKNOWN')
        except Exception:
            return 'UNKNOWN'
    
    def _parse_pil_gps(self, gps_info: Dict[int, Any]) -> Optional[GPSCoordinates]:
        """Parse GPS information from PIL format.
        
        Args:
            gps_info: GPS info dictionary from PIL
            
        Returns:
            GPSCoordinates object or None
        """
        try:
            # Convert numeric GPS tags to names
            gps_data = {}
            for tag_id, value in gps_info.items():
                tag_name = GPSTAGS.get(tag_id, tag_id)
                gps_data[tag_name] = value
            
            # Extract coordinates
            lat_data = gps_data.get('GPSLatitude')
            lat_ref = gps_data.get('GPSLatitudeRef')
            lon_data = gps_data.get('GPSLongitude')
            lon_ref = gps_data.get('GPSLongitudeRef')
            
            if all([lat_data, lat_ref, lon_data, lon_ref]):
                latitude = self._convert_dms_to_decimal(lat_data, lat_ref)
                longitude = self._convert_dms_to_decimal(lon_data, lon_ref)
                
                # Get altitude
                altitude = None
                alt_data = gps_data.get('GPSAltitude')
                alt_ref = gps_data.get('GPSAltitudeRef')
                if alt_data:
                    altitude = float(alt_data)
                    if alt_ref == 1:  # Below sea level
                        altitude = -altitude
                
                return GPSCoordinates(
                    latitude=round(latitude, self.gps_precision),
                    longitude=round(longitude, self.gps_precision),
                    altitude=altitude
                )
            
            return None
            
        except Exception as e:
            self.logger.debug(f"PIL GPS parsing failed: {str(e)}")
            return None
    
    def _convert_dms_to_decimal(self, dms_data: Tuple, ref: str) -> float:
        """Convert degrees, minutes, seconds to decimal degrees.
        
        Args:
            dms_data: Tuple of (degrees, minutes, seconds)
            ref: Reference direction ('N', 'S', 'E', 'W')
            
        Returns:
            Decimal degrees
        """
        degrees, minutes, seconds = dms_data
        decimal = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
        
        if ref in ['S', 'W']:
            decimal = -decimal
        
        return decimal
    
    def _convert_gps_coordinate(self, coord_str: str, ref: str) -> float:
        """Convert GPS coordinate string to decimal degrees.
        
        Args:
            coord_str: Coordinate string in DMS format
            ref: Reference direction
            
        Returns:
            Decimal degrees
        """
        try:
            # Parse coordinate string like "[12, 34, 56.78]" or "12/1, 34/1, 5678/100"
            coord_str = str(coord_str).strip('[]')
            parts = [part.strip() for part in coord_str.split(',')]
            
            degrees = self._parse_rational(parts[0])
            minutes = self._parse_rational(parts[1]) if len(parts) > 1 else 0
            seconds = self._parse_rational(parts[2]) if len(parts) > 2 else 0
            
            decimal = degrees + minutes / 60 + seconds / 3600
            
            if str(ref).upper() in ['S', 'W']:
                decimal = -decimal
            
            return decimal
            
        except Exception as e:
            self.logger.debug(f"GPS coordinate conversion failed: {str(e)}")
            return 0.0
    
    def _convert_gps_altitude(self, alt_str: str, ref: Optional[str]) -> Optional[float]:
        """Convert GPS altitude to float.
        
        Args:
            alt_str: Altitude string
            ref: Altitude reference (0 = above sea level, 1 = below)
            
        Returns:
            Altitude in meters or None
        """
        try:
            altitude = self._parse_rational(alt_str)
            if ref == '1':  # Below sea level
                altitude = -altitude
            return altitude
        except Exception:
            return None
    
    def _parse_rational(self, rational_str: str) -> float:
        """Parse rational number string like "123/100" or "123".
        
        Args:
            rational_str: Rational number string
            
        Returns:
            Float value
        """
        try:
            rational_str = str(rational_str).strip()
            if '/' in rational_str:
                numerator, denominator = rational_str.split('/')
                return float(numerator) / float(denominator)
            else:
                return float(rational_str)
        except Exception:
            return 0.0
    
    def _get_exif_value(self, exif_data: Dict[str, Any], field_names: List[str]) -> Optional[str]:
        """Get EXIF value by trying multiple field names.
        
        Args:
            exif_data: EXIF data dictionary
            field_names: List of possible field names to try
            
        Returns:
            String value or None if not found
        """
        for field_name in field_names:
            value = exif_data.get(field_name)
            if value:
                try:
                    str_value = str(value).strip()
                    if str_value and str_value != 'None':
                        return str_value
                except Exception:
                    continue
        return None


class ThumbnailGenerator:
    """Class for generating optimized thumbnails with smart cropping."""
    
    def __init__(self):
        """Initialize the thumbnail generator."""
        self.logger = logging.getLogger(__name__)
        
        # Standard thumbnail sizes
        self.standard_sizes = [
            (150, 150),   # Small square thumbnail
            (300, 300),   # Medium square thumbnail  
            (600, 400)    # Large rectangular thumbnail
        ]
        
        # Quality settings for different thumbnail sizes
        self.quality_settings = {
            (150, 150): {'quality': 85, 'optimize': True},
            (300, 300): {'quality': 90, 'optimize': True},
            (600, 400): {'quality': 92, 'optimize': True}
        }
        
        # Placeholder thumbnail settings
        self.placeholder_color = (200, 200, 200)  # Light gray
        self.placeholder_text_color = (100, 100, 100)  # Dark gray
    
    def generate_thumbnails(self, image_path: str, sizes: List[Tuple[int, int]] = None, 
                          output_dir: str = None) -> List[ThumbnailInfo]:
        """Generate multiple thumbnail sizes for an image.
        
        Args:
            image_path: Path to the source image
            sizes: List of (width, height) tuples for thumbnail sizes
            output_dir: Directory to save thumbnails (defaults to same as source)
            
        Returns:
            List of ThumbnailInfo objects for generated thumbnails
            
        Raises:
            IOError: If thumbnail generation fails
        """
        try:
            if not os.path.exists(image_path):
                raise FileNotFoundError(f"Source image not found: {image_path}")
            
            sizes = sizes or self.standard_sizes
            output_dir = output_dir or os.path.dirname(image_path)
            
            thumbnails = []
            base_name = os.path.splitext(os.path.basename(image_path))[0]
            
            self.logger.info(f"Generating {len(sizes)} thumbnails for {image_path}")
            
            # Open source image once
            with Image.open(image_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'LA', 'P'):
                    if img.mode == 'RGBA':
                        # Create white background for transparency
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])
                        img = background
                    else:
                        img = img.convert('RGB')
                
                # Generate each thumbnail size
                for width, height in sizes:
                    try:
                        thumbnail_info = self._generate_single_thumbnail(
                            img, width, height, base_name, output_dir
                        )
                        if thumbnail_info:
                            thumbnails.append(thumbnail_info)
                            self.logger.debug(f"Generated thumbnail: {thumbnail_info.size_label}")
                    except Exception as e:
                        self.logger.warning(f"Failed to generate {width}x{height} thumbnail: {str(e)}")
                        # Generate placeholder thumbnail
                        placeholder_info = self._generate_placeholder_thumbnail(
                            width, height, base_name, output_dir
                        )
                        if placeholder_info:
                            thumbnails.append(placeholder_info)
            
            self.logger.info(f"Successfully generated {len(thumbnails)} thumbnails")
            return thumbnails
            
        except Exception as e:
            self.logger.error(f"Thumbnail generation failed for {image_path}: {str(e)}")
            # Generate placeholder thumbnails for all requested sizes
            return self._generate_all_placeholders(sizes or self.standard_sizes, 
                                                 os.path.splitext(os.path.basename(image_path))[0],
                                                 output_dir or os.path.dirname(image_path))
    
    def _generate_single_thumbnail(self, img: Image.Image, width: int, height: int, 
                                 base_name: str, output_dir: str) -> Optional[ThumbnailInfo]:
        """Generate a single thumbnail with smart cropping.
        
        Args:
            img: Source PIL Image
            width: Target width
            height: Target height
            base_name: Base filename without extension
            output_dir: Output directory
            
        Returns:
            ThumbnailInfo object or None if generation failed
        """
        try:
            size_label = f"{width}x{height}"
            output_filename = f"{base_name}_thumb_{size_label}.jpg"
            output_path = os.path.join(output_dir, output_filename)
            
            # Determine if this is a square thumbnail
            is_square = width == height
            
            if is_square:
                # Use smart cropping for square thumbnails
                thumbnail = self._create_smart_square_thumbnail(img, width)
            else:
                # Use aspect ratio preservation for rectangular thumbnails
                thumbnail = self._create_aspect_preserving_thumbnail(img, width, height)
            
            # Apply quality optimization
            quality_settings = self.quality_settings.get((width, height), 
                                                        {'quality': 90, 'optimize': True})
            
            # Save thumbnail with progressive JPEG
            thumbnail.save(output_path, 
                         format='JPEG',
                         quality=quality_settings['quality'],
                         optimize=quality_settings['optimize'],
                         progressive=True)
            
            # Get file size
            file_size = os.path.getsize(output_path)
            
            return ThumbnailInfo(
                size_label=size_label,
                filename=output_filename,
                file_size=file_size,
                width=thumbnail.width,
                height=thumbnail.height,
                format='JPEG'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate {width}x{height} thumbnail: {str(e)}")
            return None
    
    def _create_smart_square_thumbnail(self, img: Image.Image, size: int) -> Image.Image:
        """Create a square thumbnail using smart cropping to preserve important content.
        
        Args:
            img: Source PIL Image
            size: Target size (width and height)
            
        Returns:
            Square thumbnail Image
        """
        try:
            # Get original dimensions
            orig_width, orig_height = img.size
            
            # If already square, just resize
            if orig_width == orig_height:
                return img.resize((size, size), Image.Resampling.LANCZOS)
            
            # Determine crop area using smart cropping
            if orig_width > orig_height:
                # Landscape image - crop from center horizontally
                crop_size = orig_height
                left = (orig_width - crop_size) // 2
                top = 0
                right = left + crop_size
                bottom = crop_size
            else:
                # Portrait image - crop from center vertically, but slightly towards top
                # This helps preserve faces and important content that's usually in upper portion
                crop_size = orig_width
                left = 0
                # Crop slightly towards the top (1/3 from top rather than center)
                top = max(0, (orig_height - crop_size) // 3)
                right = crop_size
                bottom = min(orig_height, top + crop_size)
            
            # Apply crop
            cropped = img.crop((left, top, right, bottom))
            
            # Resize to target size with high-quality resampling
            thumbnail = cropped.resize((size, size), Image.Resampling.LANCZOS)
            
            # Apply subtle sharpening to improve thumbnail quality
            thumbnail = thumbnail.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=2))
            
            return thumbnail
            
        except Exception as e:
            self.logger.warning(f"Smart cropping failed, using simple resize: {str(e)}")
            # Fallback to simple resize
            return img.resize((size, size), Image.Resampling.LANCZOS)
    
    def _create_aspect_preserving_thumbnail(self, img: Image.Image, max_width: int, 
                                          max_height: int) -> Image.Image:
        """Create a thumbnail that preserves aspect ratio within given dimensions.
        
        Args:
            img: Source PIL Image
            max_width: Maximum width
            max_height: Maximum height
            
        Returns:
            Aspect-preserving thumbnail Image
        """
        try:
            # Calculate scaling factor to fit within bounds
            orig_width, orig_height = img.size
            width_ratio = max_width / orig_width
            height_ratio = max_height / orig_height
            
            # Use the smaller ratio to ensure image fits within bounds
            scale_ratio = min(width_ratio, height_ratio)
            
            # Calculate new dimensions
            new_width = int(orig_width * scale_ratio)
            new_height = int(orig_height * scale_ratio)
            
            # Resize with high-quality resampling
            thumbnail = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Apply subtle sharpening
            thumbnail = thumbnail.filter(ImageFilter.UnsharpMask(radius=0.5, percent=50, threshold=2))
            
            return thumbnail
            
        except Exception as e:
            self.logger.warning(f"Aspect-preserving resize failed, using simple resize: {str(e)}")
            # Fallback to simple resize (may distort aspect ratio)
            return img.resize((max_width, max_height), Image.Resampling.LANCZOS)
    
    def _generate_placeholder_thumbnail(self, width: int, height: int, base_name: str, 
                                      output_dir: str) -> Optional[ThumbnailInfo]:
        """Generate a placeholder thumbnail for failed cases.
        
        Args:
            width: Thumbnail width
            height: Thumbnail height
            base_name: Base filename
            output_dir: Output directory
            
        Returns:
            ThumbnailInfo for placeholder or None if creation failed
        """
        try:
            size_label = f"{width}x{height}"
            output_filename = f"{base_name}_thumb_{size_label}_placeholder.jpg"
            output_path = os.path.join(output_dir, output_filename)
            
            # Create placeholder image
            placeholder = Image.new('RGB', (width, height), self.placeholder_color)
            
            # Try to add text if PIL supports it
            try:
                from PIL import ImageDraw, ImageFont
                draw = ImageDraw.Draw(placeholder)
                
                # Try to use a default font
                try:
                    font = ImageFont.load_default()
                except Exception:
                    font = None
                
                # Add placeholder text
                text = f"{width}x{height}"
                if font:
                    # Get text size and center it
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                    x = (width - text_width) // 2
                    y = (height - text_height) // 2
                    draw.text((x, y), text, fill=self.placeholder_text_color, font=font)
                else:
                    # Simple text without font
                    draw.text((width//2 - 20, height//2 - 10), text, 
                            fill=self.placeholder_text_color)
                    
            except ImportError:
                # ImageDraw not available, just use solid color
                pass
            
            # Save placeholder
            placeholder.save(output_path, format='JPEG', quality=80)
            
            file_size = os.path.getsize(output_path)
            
            self.logger.debug(f"Generated placeholder thumbnail: {size_label}")
            
            return ThumbnailInfo(
                size_label=size_label,
                filename=output_filename,
                file_size=file_size,
                width=width,
                height=height,
                format='JPEG'
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate placeholder thumbnail {width}x{height}: {str(e)}")
            return None
    
    def _generate_all_placeholders(self, sizes: List[Tuple[int, int]], base_name: str, 
                                 output_dir: str) -> List[ThumbnailInfo]:
        """Generate placeholder thumbnails for all requested sizes.
        
        Args:
            sizes: List of (width, height) tuples
            base_name: Base filename
            output_dir: Output directory
            
        Returns:
            List of ThumbnailInfo objects for placeholders
        """
        placeholders = []
        for width, height in sizes:
            placeholder_info = self._generate_placeholder_thumbnail(width, height, base_name, output_dir)
            if placeholder_info:
                placeholders.append(placeholder_info)
        return placeholders
    
    def optimize_for_progressive_loading(self, thumbnails: List[ThumbnailInfo]) -> List[ThumbnailInfo]:
        """Optimize thumbnails for progressive loading by sorting by size.
        
        Args:
            thumbnails: List of ThumbnailInfo objects
            
        Returns:
            Sorted list optimized for progressive loading (smallest first)
        """
        try:
            # Sort by total pixels (width * height) for progressive loading
            sorted_thumbnails = sorted(thumbnails, 
                                     key=lambda t: t.width * t.height)
            
            self.logger.debug(f"Optimized {len(thumbnails)} thumbnails for progressive loading")
            return sorted_thumbnails
            
        except Exception as e:
            self.logger.warning(f"Failed to optimize thumbnails for progressive loading: {str(e)}")
            return thumbnails


class MediaProcessingService:
    """Service for processing uploaded media files."""
    
    def __init__(self, storage_service: StorageService = None, processing_monitor: ProcessingMonitor = None):
        """Initialize the media processing service.
        
        Args:
            storage_service: Optional storage service instance
            processing_monitor: Optional processing monitor instance
        """
        self.storage_service = storage_service or StorageService()
        self.processing_monitor = processing_monitor or ProcessingMonitor()
        self.logger = logging.getLogger(__name__)
        self.exif_extractor = EXIFExtractor()
        self.thumbnail_generator = ThumbnailGenerator()
        self.format_converter = FormatConverter()
        self.fallback_handler = MediaProcessingFallback(self.storage_service)
        
        # Initialize optimization services
        self.cache_service = get_cache_service()
        self.temp_manager = get_temp_file_manager()
        self.cdn_service = get_cdn_service()
        
        # Processing configuration
        self.compression_profiles = {
            'high_quality': {'quality': 95, 'optimize': True},
            'balanced': {'quality': 85, 'optimize': True},
            'aggressive': {'quality': 70, 'optimize': True}
        }
        
        self.thumbnail_sizes = [
            (150, 150),
            (300, 300),
            (600, 400)
        ]
        
        self.supported_formats = {
            'input': ['JPEG', 'PNG', 'WEBP', 'HEIC', 'HEIF', 'TIFF'],
            'output': ['JPEG', 'PNG']
        }
        
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.target_compression_ratio = 0.7  # 70% size reduction target
        
    def process_uploaded_media(self, file_path: str, options: Dict[str, Any] = None) -> ProcessedMedia:
        """Process an uploaded media file with compression pipeline.
        
        Args:
            file_path: Path to the uploaded file
            options: Processing options dictionary
            
        Returns:
            ProcessedMedia object with processing results
            
        Raises:
            ValueError: If file is invalid or unsupported
            IOError: If file processing fails
        """
        start_time = datetime.now()
        options = options or {}
        result = None
        processed_path = None
        
        try:
            # Validate file
            self._validate_file(file_path)
            
            # Get original file info
            original_size = os.path.getsize(file_path)
            original_format = self._detect_format(file_path)
            
            # Initialize processing result
            result = ProcessedMedia(
                original_filename=os.path.basename(file_path),
                processed_filename=os.path.basename(file_path),
                file_size_original=original_size,
                file_size_processed=original_size,
                compression_ratio=1.0,
                format_original=original_format,
                format_processed=original_format,
                thumbnails=[],
                metadata={},
                processing_time=0.0,
                processing_status='initialized'
            )
            
            self.logger.info(f"Starting media processing for {file_path} (size: {original_size} bytes, format: {original_format})")
            result.processing_status = 'processing'
            
            # Handle format conversion if needed
            converted_path = file_path
            try:
                # Validate format and convert if necessary
                validation = self.validate_format(file_path)
                if not validation['supported']:
                    if validation['valid']:
                        self.logger.info(f"Converting unsupported format {original_format} to JPEG")
                        converted_path = self.handle_unsupported_format(file_path)
                        result.format_processed = 'JPEG'
                        self.logger.info(f"Successfully converted {original_format} to JPEG")
                    else:
                        raise ValueError(f"Invalid image file: {validation['error']}")
                elif original_format in ['HEIC', 'HEIF', 'WEBP', 'PNG', 'TIFF'] and options.get('convert_to_jpeg', True):
                    # Convert to JPEG for better compatibility and compression
                    self.logger.info(f"Converting {original_format} to JPEG for optimization")
                    converted_path = self.convert_format(file_path, 'JPEG')
                    result.format_processed = 'JPEG'
                    self.logger.info(f"Successfully converted {original_format} to JPEG")
            except Exception as e:
                self.logger.warning(f"Format conversion failed: {str(e)}")
                fallback_result = self.fallback_handler.handle_format_conversion_failure(
                    file_path, e, options.get('target_format', 'JPEG')
                )
                if fallback_result.success and fallback_result.fallback_file:
                    converted_path = fallback_result.fallback_file
                    self.logger.info(f"Format conversion fallback applied: {fallback_result.user_message}")
                else:
                    converted_path = file_path
                    self.logger.warning(f"Format conversion fallback failed: {fallback_result.user_message}")
            
            # Apply rotation correction first
            try:
                rotated_path = self._correct_image_orientation(converted_path, options)
            except Exception as e:
                self.logger.warning(f"Rotation correction failed: {str(e)}")
                orientation = options.get('orientation', 1)
                fallback_result = self.fallback_handler.handle_rotation_failure(
                    converted_path, e, orientation
                )
                if fallback_result.success and fallback_result.fallback_file:
                    rotated_path = fallback_result.fallback_file
                    self.logger.info(f"Rotation fallback applied: {fallback_result.user_message}")
                else:
                    rotated_path = converted_path
                    self.logger.warning(f"Rotation fallback failed: {fallback_result.user_message}")
            
            # Apply compression pipeline
            try:
                processed_path = self._compress_image(rotated_path, options)
            except Exception as e:
                self.logger.warning(f"Compression failed: {str(e)}")
                target_quality = options.get('quality', 85)
                fallback_result = self.fallback_handler.handle_compression_failure(
                    rotated_path, e, target_quality
                )
                if fallback_result.success and fallback_result.fallback_file:
                    processed_path = fallback_result.fallback_file
                    self.logger.info(f"Compression fallback applied: {fallback_result.user_message}")
                else:
                    processed_path = rotated_path
                    self.logger.warning(f"Compression fallback failed: {fallback_result.user_message}")
            
            # Update result with compression info
            if processed_path and processed_path != file_path:
                processed_size = os.path.getsize(processed_path)
                compression_ratio = processed_size / original_size
                
                result.processed_filename = os.path.basename(processed_path)
                result.file_size_processed = processed_size
                result.compression_ratio = compression_ratio
                result.format_processed = self._detect_format(processed_path)
                
                self.logger.info(f"Compression achieved {(1-compression_ratio)*100:.1f}% size reduction "
                               f"({original_size} -> {processed_size} bytes)")
            else:
                self.logger.info("No compression applied - using original file")
            
            # Generate thumbnails
            try:
                thumbnails = self.generate_thumbnails(processed_path or file_path, options)
                result.thumbnails = [thumbnail.__dict__ for thumbnail in thumbnails]
                self.logger.info(f"Generated {len(thumbnails)} thumbnails")
            except Exception as e:
                self.logger.warning(f"Thumbnail generation failed: {str(e)}")
                sizes = options.get('thumbnail_sizes', self.thumbnail_sizes)
                fallback_result = self.fallback_handler.handle_thumbnail_failure(
                    processed_path or file_path, e, sizes
                )
                if fallback_result.success:
                    self.logger.info(f"Thumbnail fallback applied: {fallback_result.user_message}")
                    # Create minimal thumbnail info for placeholders
                    result.thumbnails = [{
                        'size_label': f"{w}x{h}",
                        'filename': f"placeholder_{w}x{h}.jpg",
                        'file_size': 0,
                        'width': w,
                        'height': h,
                        'format': 'JPEG'
                    } for w, h in sizes]
                else:
                    result.thumbnails = []
                    self.logger.warning(f"Thumbnail fallback failed: {fallback_result.user_message}")
            
            # Extract metadata
            try:
                metadata = self.extract_and_store_metadata(processed_path or file_path)
                result.metadata = metadata
            except Exception as e:
                self.logger.warning(f"Metadata extraction failed: {str(e)}")
                fallback_result = self.fallback_handler.handle_exif_extraction_failure(
                    processed_path or file_path, e
                )
                if fallback_result.success:
                    self.logger.info(f"Metadata fallback applied: {fallback_result.user_message}")
                    # Create basic metadata from file system
                    result.metadata = self.fallback_handler._create_fallback_metadata(processed_path or file_path)
                else:
                    result.metadata = {}
                    self.logger.warning(f"Metadata fallback failed: {fallback_result.user_message}")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            result.processing_time = processing_time
            result.processing_status = 'completed'
            
            # Record processing metrics
            self.processing_monitor.record_processing_metrics(
                operation_type='media_processing',
                file_size=original_size,
                processing_time=processing_time,
                success=True,
                compression_ratio=result.compression_ratio
            )
            
            self.logger.info(f"Media processing completed in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            self.logger.error(f"Media processing failed: {str(e)}")
            
            # Record processing failure metrics
            processing_time = (datetime.now() - start_time).total_seconds()
            self.processing_monitor.record_processing_metrics(
                operation_type='media_processing',
                file_size=original_size if 'original_size' in locals() else 0,
                processing_time=processing_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            # Apply comprehensive fallback handling
            try:
                fallback_result = self.fallback_handler.handle_processing_failure(
                    file_path, e, 'media_processing_pipeline'
                )
                
                if fallback_result.success and result is not None:
                    # Update result with fallback information
                    result.processing_status = 'completed_with_fallback'
                    if fallback_result.fallback_file and fallback_result.fallback_file != file_path:
                        result.processed_filename = os.path.basename(fallback_result.fallback_file)
                        result.file_size_processed = os.path.getsize(fallback_result.fallback_file)
                        result.compression_ratio = result.file_size_processed / result.file_size_original
                    
                    # Add fallback information to metadata
                    result.metadata['fallback_applied'] = True
                    result.metadata['fallback_type'] = fallback_result.fallback_type
                    result.metadata['fallback_message'] = fallback_result.user_message
                    
                    result.processing_time = processing_time
                    
                    self.logger.info(f"Processing completed with fallback: {fallback_result.user_message}")
                    return result
                else:
                    if result is not None:
                        result.processing_status = 'failed'
                        result.metadata['error_message'] = fallback_result.user_message
                    
                    self.logger.error(f"Processing and fallback both failed: {fallback_result.user_message}")
                    
            except Exception as fallback_error:
                self.logger.error(f"Fallback handling failed: {str(fallback_error)}")
                if result is not None:
                    result.processing_status = 'failed'
            
            # Clean up processed files if they were created
            if processed_path and processed_path != file_path and os.path.exists(processed_path):
                try:
                    os.unlink(processed_path)
                except Exception:
                    pass
            # Also clean up rotated file if it exists and is different from original
            try:
                if 'rotated_path' in locals() and rotated_path and rotated_path != file_path and os.path.exists(rotated_path):
                    os.unlink(rotated_path)
            except Exception:
                pass
            raise
    
    def _validate_file(self, file_path: str) -> None:
        """Validate uploaded file.
        
        Args:
            file_path: Path to file to validate
            
        Raises:
            ValueError: If file is invalid
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError("File is empty")
        
        if file_size > self.max_file_size:
            raise ValueError(f"File too large: {file_size} bytes (max: {self.max_file_size})")
        
        # Check if file is a valid image
        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception as e:
            raise ValueError(f"Invalid image file: {str(e)}")
    
    def _detect_format(self, file_path: str) -> str:
        """Detect file format using python-magic.
        
        Args:
            file_path: Path to file
            
        Returns:
            Detected format string
        """
        try:
            mime_type = magic.from_file(file_path, mime=True)
            format_map = {
                'image/jpeg': 'JPEG',
                'image/png': 'PNG',
                'image/webp': 'WEBP',
                'image/heic': 'HEIC',
                'image/heif': 'HEIF',
                'image/tiff': 'TIFF'
            }
            return format_map.get(mime_type, 'UNKNOWN')
        except Exception as e:
            self.logger.warning(f"Could not detect format for {file_path}: {str(e)}")
            return 'UNKNOWN'
    
    def get_processing_status(self, file_id: str) -> Dict[str, Any]:
        """Get processing status for a file.
        
        Args:
            file_id: Unique identifier for the file
            
        Returns:
            Status dictionary
        """
        # TODO: Implement status tracking in future tasks
        return {
            'file_id': file_id,
            'status': 'not_implemented',
            'progress': 0,
            'message': 'Status tracking not yet implemented'
        }
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get list of supported input and output formats.
        
        Returns:
            Dictionary with input and output format lists
        """
        return self.supported_formats.copy()
    
    def get_compression_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Get available compression profiles.
        
        Returns:
            Dictionary of compression profiles
        """
        return self.compression_profiles.copy()
    
    def _compress_image(self, file_path: str, options: Dict[str, Any]) -> str:
        """Compress an image file using adaptive compression.
        
        Args:
            file_path: Path to the original image file
            options: Processing options including quality profile
            
        Returns:
            Path to compressed image file, or original path if no compression applied
            
        Raises:
            IOError: If compression fails
        """
        try:
            # Determine compression profile
            profile_name = options.get('quality', 'balanced')
            profile = self._get_adaptive_compression_profile(file_path, profile_name)
            
            # Open and analyze image
            with Image.open(file_path) as img:
                original_format = img.format
                original_size = os.path.getsize(file_path)
                
                # Skip compression for very small files
                if original_size < 50 * 1024:  # 50KB
                    self.logger.info(f"Skipping compression for small file ({original_size} bytes)")
                    return file_path
                
                # Convert to RGB if necessary for JPEG output
                if img.mode in ('RGBA', 'LA', 'P'):
                    if original_format == 'PNG' and img.mode == 'RGBA':
                        # Preserve transparency by converting to white background
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
                        img = background
                    else:
                        img = img.convert('RGB')
                
                # Create output path
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_dir = os.path.dirname(file_path)
                output_path = os.path.join(output_dir, f"{base_name}_compressed.jpg")
                
                # Apply compression with progressive JPEG
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': profile['quality'],
                    'optimize': profile['optimize'],
                    'progressive': True,  # Progressive JPEG for web optimization
                }
                
                # Add subsampling for aggressive compression
                if profile_name == 'aggressive':
                    save_kwargs['subsampling'] = 2  # 4:2:0 subsampling
                
                img.save(output_path, **save_kwargs)
                
                # Check if compression was beneficial
                compressed_size = os.path.getsize(output_path)
                compression_ratio = compressed_size / original_size
                
                if compression_ratio >= 0.95:  # Less than 5% reduction
                    self.logger.info(f"Compression not beneficial ({compression_ratio:.3f} ratio), using original")
                    os.unlink(output_path)
                    return file_path
                
                self.logger.info(f"Image compressed: {original_size} -> {compressed_size} bytes "
                               f"({compression_ratio:.3f} ratio, {profile['quality']} quality)")
                
                # Record compression metrics
                self.processing_monitor.record_processing_metrics(
                    operation_type='compression',
                    file_size=original_size,
                    processing_time=0.1,  # Approximate compression time
                    success=True,
                    compression_ratio=compression_ratio
                )
                
                return output_path
                
        except Exception as e:
            self.logger.error(f"Image compression failed: {str(e)}")
            
            # Record compression failure
            original_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            self.processing_monitor.record_processing_metrics(
                operation_type='compression',
                file_size=original_size,
                processing_time=0.1,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            # Return original file path on compression failure
            return file_path
    
    def _get_adaptive_compression_profile(self, file_path: str, profile_name: str) -> Dict[str, Any]:
        """Get adaptive compression profile based on file characteristics.
        
        Args:
            file_path: Path to the image file
            profile_name: Base profile name ('high_quality', 'balanced', 'aggressive')
            
        Returns:
            Compression profile dictionary with adaptive settings
        """
        base_profile = self.compression_profiles.get(profile_name, self.compression_profiles['balanced']).copy()
        
        try:
            file_size = os.path.getsize(file_path)
            
            # Adaptive compression based on file size
            if file_size > 5 * 1024 * 1024:  # > 5MB - more aggressive
                base_profile['quality'] = max(base_profile['quality'] - 10, 60)
                self.logger.debug(f"Large file detected ({file_size} bytes), reducing quality to {base_profile['quality']}")
            elif file_size > 2 * 1024 * 1024:  # > 2MB - slightly more aggressive
                base_profile['quality'] = max(base_profile['quality'] - 5, 70)
                self.logger.debug(f"Medium file detected ({file_size} bytes), reducing quality to {base_profile['quality']}")
            
            # Adaptive compression based on image dimensions
            with Image.open(file_path) as img:
                width, height = img.size
                total_pixels = width * height
                
                if total_pixels > 4000 * 3000:  # > 12MP - more aggressive
                    base_profile['quality'] = max(base_profile['quality'] - 5, 65)
                    self.logger.debug(f"High resolution image ({width}x{height}), reducing quality to {base_profile['quality']}")
                
        except Exception as e:
            self.logger.warning(f"Could not analyze file for adaptive compression: {str(e)}")
        
        return base_profile
    
    def _correct_image_orientation(self, file_path: str, options: Dict[str, Any]) -> str:
        """Correct image orientation based on EXIF orientation data.
        
        Args:
            file_path: Path to the original image file
            options: Processing options
            
        Returns:
            Path to orientation-corrected image file, or original path if no correction needed
            
        Raises:
            IOError: If rotation fails
        """
        try:
            # Extract EXIF data to get orientation
            exif_data = self.exif_extractor.extract_exif_data(file_path)
            
            # Get orientation value
            orientation = self._get_image_orientation(file_path, exif_data)
            
            # Check if rotation is needed
            if orientation == 1:
                self.logger.debug(f"Image {file_path} already has correct orientation")
                return file_path
            
            # Open image for rotation
            with Image.open(file_path) as img:
                # Preserve original format and quality
                original_format = img.format
                
                # Apply rotation based on orientation
                rotated_img = self._apply_orientation_correction(img, orientation)
                
                if rotated_img is None:
                    self.logger.debug(f"No rotation needed for orientation {orientation}")
                    return file_path
                
                # Create output path
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                output_dir = os.path.dirname(file_path)
                output_path = os.path.join(output_dir, f"{base_name}_rotated.{original_format.lower()}")
                
                # Prepare save parameters to preserve quality
                save_kwargs = {'format': original_format}
                
                if original_format == 'JPEG':
                    save_kwargs.update({
                        'quality': 95,  # High quality to preserve image quality
                        'optimize': True,
                        'progressive': True
                    })
                elif original_format == 'PNG':
                    save_kwargs.update({
                        'optimize': True,
                        'compress_level': 6
                    })
                
                # Save rotated image
                rotated_img.save(output_path, **save_kwargs)
                
                # Update EXIF orientation tag to 1 (normal)
                self._update_exif_orientation(output_path, 1)
                
                self.logger.info(f"Image rotated from orientation {orientation} to normal: {output_path}")
                return output_path
                
        except Exception as e:
            self.logger.error(f"Image rotation correction failed: {str(e)}")
            # Return original file path on rotation failure
            return file_path
    
    def _get_image_orientation(self, file_path: str, exif_data: Dict[str, Any]) -> int:
        """Get image orientation from EXIF data or PIL.
        
        Args:
            file_path: Path to image file
            exif_data: Extracted EXIF data
            
        Returns:
            Orientation value (1-8), defaults to 1 if not found
        """
        try:
            # Try to get orientation from EXIF data first
            orientation_fields = ['Orientation', 'Image Orientation', 'EXIF Orientation']
            
            for field in orientation_fields:
                orientation = exif_data.get(field)
                if orientation is not None:
                    try:
                        orientation_int = int(str(orientation).strip())
                        if 1 <= orientation_int <= 8:
                            self.logger.debug(f"Found orientation {orientation_int} from EXIF field {field}")
                            return orientation_int
                    except (ValueError, TypeError):
                        continue
            
            # Try to get orientation directly from PIL
            try:
                with Image.open(file_path) as img:
                    pil_exif = img.getexif()
                    if pil_exif:
                        orientation = pil_exif.get(274)  # 274 is the orientation tag ID
                        if orientation and 1 <= orientation <= 8:
                            self.logger.debug(f"Found orientation {orientation} from PIL EXIF")
                            return orientation
            except Exception as e:
                self.logger.debug(f"Could not get orientation from PIL: {str(e)}")
            
            # Default to normal orientation
            self.logger.debug("No orientation data found, defaulting to 1 (normal)")
            return 1
            
        except Exception as e:
            self.logger.warning(f"Error getting image orientation: {str(e)}")
            return 1
    
    def _apply_orientation_correction(self, img: Image.Image, orientation: int) -> Optional[Image.Image]:
        """Apply orientation correction to an image.
        
        Args:
            img: PIL Image object
            orientation: EXIF orientation value (1-8)
            
        Returns:
            Rotated Image object or None if no rotation needed
        """
        try:
            # EXIF orientation values and their corrections:
            # 1: Normal (no rotation needed)
            # 2: Mirrored horizontally
            # 3: Rotated 180°
            # 4: Mirrored vertically
            # 5: Mirrored horizontally and rotated 270° CW
            # 6: Rotated 90° CW
            # 7: Mirrored horizontally and rotated 90° CW
            # 8: Rotated 270° CW
            
            if orientation == 1:
                return None  # No correction needed
            elif orientation == 2:
                # Horizontal mirror
                return img.transpose(Image.FLIP_LEFT_RIGHT)
            elif orientation == 3:
                # 180° rotation
                return img.rotate(180, expand=True)
            elif orientation == 4:
                # Vertical mirror
                return img.transpose(Image.FLIP_TOP_BOTTOM)
            elif orientation == 5:
                # Horizontal mirror + 270° CW rotation
                return img.transpose(Image.FLIP_LEFT_RIGHT).rotate(270, expand=True)
            elif orientation == 6:
                # 90° CW rotation
                return img.rotate(270, expand=True)
            elif orientation == 7:
                # Horizontal mirror + 90° CW rotation
                return img.transpose(Image.FLIP_LEFT_RIGHT).rotate(90, expand=True)
            elif orientation == 8:
                # 270° CW rotation
                return img.rotate(90, expand=True)
            else:
                self.logger.warning(f"Invalid orientation value: {orientation}")
                return None
                
        except Exception as e:
            self.logger.error(f"Failed to apply orientation correction: {str(e)}")
            return None
    
    def _update_exif_orientation(self, file_path: str, new_orientation: int) -> None:
        """Update EXIF orientation tag after rotation.
        
        Args:
            file_path: Path to image file
            new_orientation: New orientation value (typically 1 for normal)
        """
        try:
            # For JPEG files, we can update the EXIF orientation tag
            if file_path.lower().endswith(('.jpg', '.jpeg')):
                with Image.open(file_path) as img:
                    # Get existing EXIF data
                    exif_dict = img.getexif()
                    
                    # Update orientation tag (274 is the orientation tag ID)
                    exif_dict[274] = new_orientation
                    
                    # Save with updated EXIF
                    img.save(file_path, exif=exif_dict, quality=95, optimize=True)
                    
                    self.logger.debug(f"Updated EXIF orientation to {new_orientation} for {file_path}")
            else:
                self.logger.debug(f"EXIF orientation update not supported for {file_path}")
                
        except Exception as e:
            self.logger.warning(f"Could not update EXIF orientation: {str(e)}")
    
    def calculate_compression_ratio(self, original_size: int, compressed_size: int) -> float:
        """Calculate compression ratio.
        
        Args:
            original_size: Original file size in bytes
            compressed_size: Compressed file size in bytes
            
        Returns:
            Compression ratio (compressed_size / original_size)
        """
        if original_size == 0:
            return 1.0
        return compressed_size / original_size
    
    def get_compression_stats(self, original_size: int, compressed_size: int) -> Dict[str, Any]:
        """Get detailed compression statistics.
        
        Args:
            original_size: Original file size in bytes
            compressed_size: Compressed file size in bytes
            
        Returns:
            Dictionary with compression statistics
        """
        ratio = self.calculate_compression_ratio(original_size, compressed_size)
        reduction_percent = (1 - ratio) * 100
        space_saved = original_size - compressed_size
        
        return {
            'original_size': original_size,
            'compressed_size': compressed_size,
            'compression_ratio': ratio,
            'reduction_percent': reduction_percent,
            'space_saved_bytes': space_saved,
            'space_saved_mb': space_saved / (1024 * 1024)
        }
    
    def extract_and_store_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract and store metadata from an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary containing extracted metadata
        """
        try:
            # Check if file exists first
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Extract raw EXIF data
            exif_data = self.exif_extractor.extract_exif_data(file_path)
            
            # Extract structured metadata
            metadata = {
                'exif_raw': exif_data,
                'timestamp_original': None,
                'timestamp_processed': datetime.now(),
                'gps_coordinates': None,
                'location_name': None,
                'camera_info': None,
                'image_dimensions': None,
                'orientation': 1
            }
            
            # Extract timestamp
            timestamp = self.exif_extractor.get_timestamp(exif_data)
            if timestamp:
                metadata['timestamp_original'] = timestamp.isoformat()
            
            # Extract GPS coordinates
            gps_coords = self.exif_extractor.get_gps_coordinates(exif_data)
            if gps_coords:
                metadata['gps_coordinates'] = {
                    'latitude': gps_coords.latitude,
                    'longitude': gps_coords.longitude,
                    'altitude': gps_coords.altitude
                }
                
                # TODO: Convert GPS coordinates to human-readable location
                # This would require a geocoding service integration
                metadata['location_name'] = f"{gps_coords.latitude:.4f}, {gps_coords.longitude:.4f}"
            
            # Extract camera information
            camera_info = self.exif_extractor.get_camera_info(exif_data)
            if camera_info:
                metadata['camera_info'] = {
                    'make': camera_info.make,
                    'model': camera_info.model,
                    'software': camera_info.software,
                    'lens_make': camera_info.lens_make,
                    'lens_model': camera_info.lens_model,
                    'focal_length': camera_info.focal_length,
                    'aperture': camera_info.aperture,
                    'iso': camera_info.iso,
                    'exposure_time': camera_info.exposure_time,
                    'flash': camera_info.flash
                }
            
            # Get image dimensions and orientation
            try:
                with Image.open(file_path) as img:
                    metadata['image_dimensions'] = {
                        'width': img.width,
                        'height': img.height
                    }
                    
                    # Get orientation from EXIF
                    orientation = exif_data.get('Orientation', 1)
                    if isinstance(orientation, str):
                        try:
                            orientation = int(orientation)
                        except ValueError:
                            orientation = 1
                    metadata['orientation'] = orientation
                    
            except Exception as e:
                self.logger.warning(f"Could not get image dimensions: {str(e)}")
            
            self.logger.info(f"Successfully extracted metadata from {file_path}")
            return metadata
            
        except Exception as e:
            self.logger.error(f"Metadata extraction failed for {file_path}: {str(e)}")
            return {
                'timestamp_processed': datetime.now().isoformat(),
                'error': str(e)
            }
    
    def generate_thumbnails(self, image_path: str, options: Dict[str, Any] = None) -> List[ThumbnailInfo]:
        """Generate optimized thumbnails for an image.
        
        Args:
            image_path: Path to the source image
            options: Processing options including custom thumbnail sizes
            
        Returns:
            List of ThumbnailInfo objects for generated thumbnails
            
        Raises:
            IOError: If thumbnail generation fails
        """
        try:
            options = options or {}
            
            # Get thumbnail sizes from options or use defaults
            custom_sizes = options.get('thumbnail_sizes')
            if custom_sizes:
                # Validate custom sizes
                sizes = []
                for size in custom_sizes:
                    if isinstance(size, (list, tuple)) and len(size) == 2:
                        width, height = size
                        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
                            sizes.append((width, height))
                        else:
                            self.logger.warning(f"Invalid thumbnail size: {size}")
                    else:
                        self.logger.warning(f"Invalid thumbnail size format: {size}")
                
                if not sizes:
                    self.logger.warning("No valid custom thumbnail sizes, using defaults")
                    sizes = None
            else:
                sizes = None
            
            # Generate thumbnails using the thumbnail generator
            start_time = time.time()
            thumbnails = self.thumbnail_generator.generate_thumbnails(
                image_path=image_path,
                sizes=sizes,
                output_dir=os.path.dirname(image_path)
            )
            
            # Optimize for progressive loading
            optimized_thumbnails = self.thumbnail_generator.optimize_for_progressive_loading(thumbnails)
            processing_time = time.time() - start_time
            
            # Record thumbnail generation metrics
            file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
            self.processing_monitor.record_processing_metrics(
                operation_type='thumbnail_generation',
                file_size=file_size,
                processing_time=processing_time,
                success=True
            )
            
            self.logger.info(f"Successfully generated {len(optimized_thumbnails)} thumbnails for {image_path}")
            return optimized_thumbnails
            
        except Exception as e:
            self.logger.error(f"Thumbnail generation failed for {image_path}: {str(e)}")
            
            # Record thumbnail generation failure
            file_size = os.path.getsize(image_path) if os.path.exists(image_path) else 0
            processing_time = time.time() - start_time if 'start_time' in locals() else 0
            self.processing_monitor.record_processing_metrics(
                operation_type='thumbnail_generation',
                file_size=file_size,
                processing_time=processing_time,
                success=False,
                error_type=type(e).__name__,
                error_message=str(e)
            )
            
            raise IOError(f"Thumbnail generation failed: {str(e)}")
    
    def get_thumbnail_sizes(self) -> List[Tuple[int, int]]:
        """Get the standard thumbnail sizes.
        
        Returns:
            List of (width, height) tuples for standard thumbnail sizes
        """
        return self.thumbnail_generator.standard_sizes.copy()
    
    def convert_format(self, input_path: str, target_format: str = 'JPEG', 
                      output_path: str = None, quality: int = None) -> str:
        """Convert image to target format.
        
        Args:
            input_path: Path to input image
            target_format: Target format ('JPEG' or 'PNG')
            output_path: Output path (optional, auto-generated if not provided)
            quality: Conversion quality (optional, uses format defaults)
            
        Returns:
            Path to converted image
            
        Raises:
            ValueError: If format is not supported
            IOError: If conversion fails
        """
        try:
            if target_format not in self.supported_formats['output']:
                raise ValueError(f"Unsupported target format: {target_format}")
            
            if target_format == 'JPEG':
                return self.format_converter.convert_to_jpeg(
                    input_path=input_path,
                    output_path=output_path,
                    quality=quality
                )
            else:
                raise ValueError(f"Conversion to {target_format} not yet implemented")
                
        except Exception as e:
            self.logger.error(f"Format conversion failed: {str(e)}")
            raise
    
    def validate_format(self, file_path: str) -> Dict[str, Any]:
        """Validate image format and check if it's supported.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Dictionary containing validation results
        """
        return self.format_converter.validate_format(file_path)
    
    def handle_unsupported_format(self, input_path: str, output_path: str = None) -> str:
        """Handle unsupported format by attempting conversion.
        
        Args:
            input_path: Path to input file
            output_path: Path for output file (optional)
            
        Returns:
            Path to converted file
            
        Raises:
            ValueError: If format cannot be converted
            IOError: If conversion fails
        """
        try:
            return self.format_converter.convert_unsupported_format(input_path, output_path)
        except Exception as e:
            self.logger.error(f"Unsupported format handling failed: {str(e)}")
            raise
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get supported input and output formats.
        
        Returns:
            Dictionary with supported format lists
        """
        return self.format_converter.get_supported_formats()
    
    def process_and_store_media(self, file_path: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process media file and store all versions using enhanced StorageService.
        
        Args:
            file_path: Path to the original media file
            options: Processing options
            
        Returns:
            Dictionary containing processing results and storage information
            
        Raises:
            IOError: If processing or storage fails
        """
        try:
            options = options or {}
            
            # Process the media file
            processing_result = self.process_uploaded_media(file_path, options)
            
            # Determine processed file path
            processed_file_path = file_path
            if processing_result.processed_filename and processing_result.processed_filename != processing_result.original_filename:
                processed_file_path = os.path.join(
                    os.path.dirname(file_path),
                    processing_result.processed_filename
                )
            
            # Initialize storage service
            storage_service = StorageService()
            
            # Store processed media with all versions
            storage_info = storage_service.store_processed_media(
                original_file_path=file_path,
                processed_file_path=processed_file_path,
                thumbnails=processing_result.thumbnails,
                metadata=processing_result.metadata
            )
            
            # Combine processing and storage results
            complete_result = {
                'processing': {
                    'original_filename': processing_result.original_filename,
                    'processed_filename': processing_result.processed_filename,
                    'file_size_original': processing_result.file_size_original,
                    'file_size_processed': processing_result.file_size_processed,
                    'compression_ratio': processing_result.compression_ratio,
                    'format_original': processing_result.format_original,
                    'format_processed': processing_result.format_processed,
                    'processing_time': processing_result.processing_time,
                    'processing_status': processing_result.processing_status,
                    'thumbnail_count': len(processing_result.thumbnails)
                },
                'storage': storage_info,
                'metadata': processing_result.metadata
            }
            
            # Clean up temporary processing files
            temp_files_to_cleanup = []
            
            # Add processed file to cleanup if it's different from original
            if processed_file_path != file_path and os.path.exists(processed_file_path):
                temp_files_to_cleanup.append(processed_file_path)
            
            # Add thumbnail files to cleanup
            original_dir = os.path.dirname(file_path)
            for thumbnail in processing_result.thumbnails:
                if isinstance(thumbnail, dict):
                    thumbnail_filename = thumbnail.get('filename')
                else:
                    thumbnail_filename = thumbnail.filename
                
                if thumbnail_filename:
                    thumbnail_path = os.path.join(original_dir, thumbnail_filename)
                    if os.path.exists(thumbnail_path):
                        temp_files_to_cleanup.append(thumbnail_path)
            
            # Clean up temporary files
            if temp_files_to_cleanup:
                storage_service.cleanup_failed_processing(temp_files_to_cleanup)
            
            self.logger.info(f"Successfully processed and stored media: {processing_result.original_filename}")
            return complete_result
            
        except Exception as e:
            self.logger.error(f"Media processing and storage failed: {str(e)}")
            
            # Clean up any temporary files on failure
            try:
                storage_service = StorageService()
                temp_files = []
                
                # Try to clean up processed file if it exists and is different from original
                if 'processed_file_path' in locals() and processed_file_path != file_path:
                    if os.path.exists(processed_file_path):
                        temp_files.append(processed_file_path)
                
                # Try to clean up any thumbnail files
                if 'processing_result' in locals() and hasattr(processing_result, 'thumbnails'):
                    original_dir = os.path.dirname(file_path)
                    for thumbnail in processing_result.thumbnails:
                        if isinstance(thumbnail, dict):
                            thumbnail_filename = thumbnail.get('filename')
                        else:
                            thumbnail_filename = thumbnail.filename
                        
                        if thumbnail_filename:
                            thumbnail_path = os.path.join(original_dir, thumbnail_filename)
                            if os.path.exists(thumbnail_path):
                                temp_files.append(thumbnail_path)
                
                if temp_files:
                    storage_service.cleanup_failed_processing(temp_files)
                    
            except Exception as cleanup_error:
                self.logger.warning(f"Failed to clean up temporary files: {str(cleanup_error)}")
            
            raise IOError(f"Media processing and storage failed: {str(e)}")

class FormatConverter:
    """Class for converting between different image formats with quality preservation."""
    
    def __init__(self):
        """Initialize the format converter."""
        self.logger = logging.getLogger(__name__)
        
        # Supported input and output formats
        self.supported_formats = {
            'input': ['JPEG', 'PNG', 'WEBP', 'HEIC', 'HEIF', 'TIFF'],
            'output': ['JPEG', 'PNG']
        }
        
        # Format conversion quality settings
        self.conversion_quality = {
            'HEIC': {'quality': 95, 'preserve_metadata': True},
            'HEIF': {'quality': 95, 'preserve_metadata': True},
            'WEBP': {'quality': 92, 'preserve_metadata': True},
            'PNG': {'quality': 90, 'preserve_metadata': False},  # PNG to JPEG loses transparency
            'TIFF': {'quality': 95, 'preserve_metadata': True}
        }
        
        # PNG transparency handling options
        self.png_background_color = (255, 255, 255)  # White background
        
        # Initialize HEIF support
        self._init_heif_support()
    
    def _init_heif_support(self):
        """Initialize HEIF/HEIC support if available."""
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
            self.heif_supported = True
            self.logger.debug("HEIF/HEIC support initialized successfully")
        except ImportError:
            self.heif_supported = False
            self.logger.warning("pillow-heif not available, HEIC/HEIF conversion disabled")
        except Exception as e:
            self.heif_supported = False
            self.logger.warning(f"Failed to initialize HEIF support: {str(e)}")
    
    def convert_to_jpeg(self, input_path: str, output_path: str = None, 
                       quality: int = None, preserve_transparency: bool = True) -> str:
        """Convert an image to JPEG format.
        
        Args:
            input_path: Path to the input image
            output_path: Path for the output JPEG (optional, defaults to input path with .jpg extension)
            quality: JPEG quality (1-100, optional, uses format-specific default)
            preserve_transparency: Whether to preserve PNG transparency with white background
            
        Returns:
            Path to the converted JPEG file
            
        Raises:
            ValueError: If input format is not supported
            IOError: If conversion fails
        """
        try:
            if not os.path.exists(input_path):
                raise FileNotFoundError(f"Input file not found: {input_path}")
            
            # Detect input format
            input_format = self._detect_format(input_path)
            if input_format not in self.supported_formats['input']:
                raise ValueError(f"Unsupported input format: {input_format}")
            
            # Generate output path if not provided
            if output_path is None:
                base_name = os.path.splitext(input_path)[0]
                output_path = f"{base_name}.jpg"
            
            # Get quality setting
            if quality is None:
                quality = self.conversion_quality.get(input_format, {}).get('quality', 90)
            
            self.logger.info(f"Converting {input_format} to JPEG: {input_path} -> {output_path}")
            
            # Handle different input formats
            if input_format in ['HEIC', 'HEIF']:
                return self._convert_heic_to_jpeg(input_path, output_path, quality)
            elif input_format == 'WEBP':
                return self._convert_webp_to_jpeg(input_path, output_path, quality)
            elif input_format == 'PNG':
                return self._convert_png_to_jpeg(input_path, output_path, quality, preserve_transparency)
            elif input_format == 'TIFF':
                return self._convert_tiff_to_jpeg(input_path, output_path, quality)
            elif input_format == 'JPEG':
                # Already JPEG, just copy or re-compress if quality is different
                return self._recompress_jpeg(input_path, output_path, quality)
            else:
                raise ValueError(f"Conversion from {input_format} not implemented")
                
        except Exception as e:
            self.logger.error(f"Format conversion failed for {input_path}: {str(e)}")
            raise IOError(f"Format conversion failed: {str(e)}")
    
    def _convert_heic_to_jpeg(self, input_path: str, output_path: str, quality: int) -> str:
        """Convert HEIC/HEIF to JPEG.
        
        Args:
            input_path: Path to HEIC/HEIF file
            output_path: Path for output JPEG
            quality: JPEG quality
            
        Returns:
            Path to converted JPEG file
        """
        if not self.heif_supported:
            raise ValueError("HEIC/HEIF conversion not supported - pillow-heif not available")
        
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Preserve EXIF data if available
                exif_dict = None
                if hasattr(img, '_getexif') and img._getexif():
                    exif_dict = img._getexif()
                
                # Save as JPEG with high quality
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': quality,
                    'optimize': True,
                    'progressive': True
                }
                
                # Add EXIF data if available
                if exif_dict:
                    try:
                        save_kwargs['exif'] = img.info.get('exif', b'')
                    except Exception:
                        self.logger.debug("Could not preserve EXIF data in HEIC conversion")
                
                img.save(output_path, **save_kwargs)
            
            self.logger.debug(f"Successfully converted HEIC/HEIF to JPEG: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"HEIC/HEIF to JPEG conversion failed: {str(e)}")
            raise
    
    def _convert_webp_to_jpeg(self, input_path: str, output_path: str, quality: int) -> str:
        """Convert WebP to JPEG.
        
        Args:
            input_path: Path to WebP file
            output_path: Path for output JPEG
            quality: JPEG quality
            
        Returns:
            Path to converted JPEG file
        """
        try:
            with Image.open(input_path) as img:
                # Handle transparency in WebP
                if img.mode in ('RGBA', 'LA'):
                    # Create white background
                    background = Image.new('RGB', img.size, self.png_background_color)
                    if img.mode == 'RGBA':
                        background.paste(img, mask=img.split()[-1])
                    else:
                        background.paste(img, mask=img.split()[-1])
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPEG
                img.save(output_path, 
                        format='JPEG',
                        quality=quality,
                        optimize=True,
                        progressive=True)
            
            self.logger.debug(f"Successfully converted WebP to JPEG: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"WebP to JPEG conversion failed: {str(e)}")
            raise
    
    def _convert_png_to_jpeg(self, input_path: str, output_path: str, quality: int, 
                           preserve_transparency: bool) -> str:
        """Convert PNG to JPEG.
        
        Args:
            input_path: Path to PNG file
            output_path: Path for output JPEG
            quality: JPEG quality
            preserve_transparency: Whether to use white background for transparency
            
        Returns:
            Path to converted JPEG file
        """
        try:
            with Image.open(input_path) as img:
                # Handle transparency
                if img.mode in ('RGBA', 'LA', 'P'):
                    if preserve_transparency and img.mode in ('RGBA', 'LA'):
                        # Create background with specified color
                        background = Image.new('RGB', img.size, self.png_background_color)
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img, mask=img.split()[-1])
                        img = background
                    else:
                        # Convert palette or transparency to RGB
                        img = img.convert('RGB')
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Save as JPEG
                img.save(output_path,
                        format='JPEG',
                        quality=quality,
                        optimize=True,
                        progressive=True)
            
            self.logger.debug(f"Successfully converted PNG to JPEG: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"PNG to JPEG conversion failed: {str(e)}")
            raise
    
    def _convert_tiff_to_jpeg(self, input_path: str, output_path: str, quality: int) -> str:
        """Convert TIFF to JPEG.
        
        Args:
            input_path: Path to TIFF file
            output_path: Path for output JPEG
            quality: JPEG quality
            
        Returns:
            Path to converted JPEG file
        """
        try:
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode != 'RGB':
                    if img.mode in ('RGBA', 'LA'):
                        # Handle transparency
                        background = Image.new('RGB', img.size, self.png_background_color)
                        if img.mode == 'RGBA':
                            background.paste(img, mask=img.split()[-1])
                        else:
                            background.paste(img, mask=img.split()[-1])
                        img = background
                    else:
                        img = img.convert('RGB')
                
                # Preserve EXIF data if available
                exif_data = img.info.get('exif', b'')
                
                # Save as JPEG
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': quality,
                    'optimize': True,
                    'progressive': True
                }
                
                if exif_data:
                    save_kwargs['exif'] = exif_data
                
                img.save(output_path, **save_kwargs)
            
            self.logger.debug(f"Successfully converted TIFF to JPEG: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"TIFF to JPEG conversion failed: {str(e)}")
            raise
    
    def _recompress_jpeg(self, input_path: str, output_path: str, quality: int) -> str:
        """Re-compress JPEG with different quality settings.
        
        Args:
            input_path: Path to input JPEG
            output_path: Path for output JPEG
            quality: Target JPEG quality
            
        Returns:
            Path to recompressed JPEG file
        """
        try:
            # If paths are the same and we're not changing quality significantly, just copy
            if input_path == output_path:
                return input_path
            
            with Image.open(input_path) as img:
                # Preserve EXIF data
                exif_data = img.info.get('exif', b'')
                
                save_kwargs = {
                    'format': 'JPEG',
                    'quality': quality,
                    'optimize': True,
                    'progressive': True
                }
                
                if exif_data:
                    save_kwargs['exif'] = exif_data
                
                img.save(output_path, **save_kwargs)
            
            self.logger.debug(f"Successfully recompressed JPEG: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"JPEG recompression failed: {str(e)}")
            raise
    
    def validate_format(self, file_path: str) -> Dict[str, Any]:
        """Validate image format and return format information.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary containing format validation results
        """
        try:
            if not os.path.exists(file_path):
                return {
                    'valid': False,
                    'format': None,
                    'supported': False,
                    'error': 'File not found'
                }
            
            # Detect format
            detected_format = self._detect_format(file_path)
            
            # Check if format is supported
            supported = detected_format in self.supported_formats['input']
            
            # Additional validation for specific formats
            validation_result = {
                'valid': True,
                'format': detected_format,
                'supported': supported,
                'error': None
            }
            
            # Special validation for HEIC/HEIF
            if detected_format in ['HEIC', 'HEIF'] and not self.heif_supported:
                validation_result.update({
                    'supported': False,
                    'error': 'HEIC/HEIF support not available - pillow-heif not installed'
                })
            
            # Try to open the file to validate it's not corrupted
            try:
                with Image.open(file_path) as img:
                    validation_result['dimensions'] = img.size
                    validation_result['mode'] = img.mode
            except Exception as e:
                validation_result.update({
                    'valid': False,
                    'error': f'Corrupted or invalid image file: {str(e)}'
                })
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'format': None,
                'supported': False,
                'error': f'Format validation failed: {str(e)}'
            }
    
    def _detect_format(self, file_path: str) -> str:
        """Detect image format using magic library and PIL.
        
        Args:
            file_path: Path to image file
            
        Returns:
            Format string (e.g., 'JPEG', 'PNG', 'WEBP', 'HEIC', 'HEIF')
        """
        try:
            # Try magic library first for accurate MIME type detection
            mime_type = magic.from_file(file_path, mime=True)
            format_map = {
                'image/jpeg': 'JPEG',
                'image/png': 'PNG',
                'image/webp': 'WEBP',
                'image/heic': 'HEIC',
                'image/heif': 'HEIF',
                'image/tiff': 'TIFF'
            }
            
            detected_format = format_map.get(mime_type)
            if detected_format:
                return detected_format
            
            # Fallback to PIL format detection
            try:
                with Image.open(file_path) as img:
                    return img.format or 'UNKNOWN'
            except Exception:
                pass
            
            # Final fallback to file extension
            ext = os.path.splitext(file_path)[1].lower()
            ext_map = {
                '.jpg': 'JPEG',
                '.jpeg': 'JPEG',
                '.png': 'PNG',
                '.webp': 'WEBP',
                '.heic': 'HEIC',
                '.heif': 'HEIF',
                '.tiff': 'TIFF',
                '.tif': 'TIFF'
            }
            
            return ext_map.get(ext, 'UNKNOWN')
            
        except Exception as e:
            self.logger.warning(f"Format detection failed for {file_path}: {str(e)}")
            return 'UNKNOWN'
    
    def get_supported_formats(self) -> Dict[str, List[str]]:
        """Get list of supported input and output formats.
        
        Returns:
            Dictionary with 'input' and 'output' format lists
        """
        supported = self.supported_formats.copy()
        
        # Remove HEIC/HEIF from input formats if not supported
        if not self.heif_supported:
            supported['input'] = [fmt for fmt in supported['input'] 
                                if fmt not in ['HEIC', 'HEIF']]
        
        return supported
    
    def convert_unsupported_format(self, input_path: str, output_path: str = None) -> str:
        """Attempt to convert an unsupported format to JPEG.
        
        Args:
            input_path: Path to input file
            output_path: Path for output file (optional)
            
        Returns:
            Path to converted file
            
        Raises:
            ValueError: If format cannot be converted
            IOError: If conversion fails
        """
        try:
            # Validate input format
            validation = self.validate_format(input_path)
            
            if validation['valid'] and validation['supported']:
                # Format is already supported, just convert to JPEG
                return self.convert_to_jpeg(input_path, output_path)
            
            if not validation['valid']:
                raise ValueError(f"Invalid or corrupted image file: {validation['error']}")
            
            # Try to convert unsupported format
            detected_format = validation['format']
            
            if detected_format in ['HEIC', 'HEIF'] and not self.heif_supported:
                raise ValueError("HEIC/HEIF conversion requires pillow-heif library")
            
            # For truly unsupported formats, try PIL's generic conversion
            try:
                if output_path is None:
                    base_name = os.path.splitext(input_path)[0]
                    output_path = f"{base_name}.jpg"
                
                with Image.open(input_path) as img:
                    if img.mode != 'RGB':
                        if img.mode in ('RGBA', 'LA'):
                            background = Image.new('RGB', img.size, self.png_background_color)
                            if img.mode == 'RGBA':
                                background.paste(img, mask=img.split()[-1])
                            else:
                                background.paste(img, mask=img.split()[-1])
                            img = background
                        else:
                            img = img.convert('RGB')
                    
                    img.save(output_path,
                            format='JPEG',
                            quality=90,
                            optimize=True,
                            progressive=True)
                
                self.logger.info(f"Successfully converted unsupported format {detected_format} to JPEG")
                return output_path
                
            except Exception as e:
                raise ValueError(f"Cannot convert format {detected_format}: {str(e)}")
                
        except Exception as e:
            self.logger.error(f"Unsupported format conversion failed for {input_path}: {str(e)}")
            raise
    
    # Processing Monitor Integration Methods
    
    def get_processing_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """Get processing statistics from the monitor.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Dictionary containing processing statistics
        """
        return self.processing_monitor.get_processing_statistics(hours)
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary from the monitor.
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            Dictionary containing error summary
        """
        return self.processing_monitor.get_error_summary(hours)
    
    def get_storage_status(self) -> Dict[str, Any]:
        """Get current storage status from the monitor.
        
        Returns:
            Dictionary containing storage status information
        """
        return self.processing_monitor.get_storage_status()
    
    def detect_performance_degradation(self) -> Dict[str, Any]:
        """Detect performance degradation using the monitor.
        
        Returns:
            Dictionary containing degradation analysis
        """
        return self.processing_monitor.detect_performance_degradation()
    
    def suggest_performance_adjustments(self) -> Dict[str, Any]:
        """Get performance adjustment suggestions from the monitor.
        
        Returns:
            Dictionary containing adjustment suggestions
        """
        return self.processing_monitor.suggest_performance_adjustments()
    
    def apply_automatic_adjustments(self) -> Dict[str, Any]:
        """Apply automatic performance adjustments using the monitor.
        
        Returns:
            Dictionary containing applied adjustments
        """
        return self.processing_monitor.apply_automatic_adjustments()
    
    def start_monitoring(self) -> None:
        """Start background performance monitoring."""
        self.processing_monitor.start_monitoring()
        self.logger.info("Background performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background performance monitoring."""
        self.processing_monitor.stop_monitoring()
        self.logger.info("Background performance monitoring stopped")
    
    def export_monitoring_data(self, output_path: str = None, format: str = 'json') -> str:
        """Export monitoring data to file.
        
        Args:
            output_path: Path to save metrics file (optional)
            format: Export format ('json' or 'csv')
            
        Returns:
            Path to exported file
        """
        return self.processing_monitor.export_metrics(output_path, format)
    
    # Error Handling and Fallback Methods
    
    def get_user_friendly_error_message(self, error: Exception, processing_step: str = None) -> str:
        """Get user-friendly error message for an exception.
        
        Args:
            error: The exception that occurred
            processing_step: Optional processing step name
            
        Returns:
            User-friendly error message
        """
        try:
            error_type = self.fallback_handler._classify_error(error, "", processing_step or "unknown")
            return self.fallback_handler.get_user_friendly_error_message(error_type)
        except Exception:
            return "An unexpected error occurred during processing. Please try again."
    
    def get_suggested_action(self, error: Exception, processing_step: str = None) -> str:
        """Get suggested action for an exception.
        
        Args:
            error: The exception that occurred
            processing_step: Optional processing step name
            
        Returns:
            Suggested action message
        """
        try:
            error_type = self.fallback_handler._classify_error(error, "", processing_step or "unknown")
            return self.fallback_handler.get_suggested_action(error_type)
        except Exception:
            return "Please try again or contact support if the problem persists."
    
    def is_error_recoverable(self, error: Exception, processing_step: str = None) -> bool:
        """Check if an error is recoverable.
        
        Args:
            error: The exception that occurred
            processing_step: Optional processing step name
            
        Returns:
            True if error is recoverable, False otherwise
        """
        try:
            error_type = self.fallback_handler._classify_error(error, "", processing_step or "unknown")
            return self.fallback_handler.is_error_recoverable(error_type)
        except Exception:
            return True  # Default to recoverable for safety
    
    def handle_processing_error_with_fallback(self, file_path: str, error: Exception, 
                                            processing_step: str, **kwargs) -> Dict[str, Any]:
        """Handle processing error with comprehensive fallback.
        
        Args:
            file_path: Path to the file being processed
            error: The exception that occurred
            processing_step: Name of the processing step that failed
            **kwargs: Additional context information
            
        Returns:
            Dictionary with error handling results
        """
        try:
            fallback_result = self.fallback_handler.handle_processing_failure(
                file_path, error, processing_step, **kwargs
            )
            
            return {
                'success': fallback_result.success,
                'fallback_type': fallback_result.fallback_type,
                'fallback_file': fallback_result.fallback_file,
                'user_message': fallback_result.user_message,
                'error_message': fallback_result.error_message,
                'is_recoverable': self.is_error_recoverable(error, processing_step)
            }
            
        except Exception as fallback_error:
            self.logger.error(f"Error handling with fallback failed: {str(fallback_error)}")
            return {
                'success': False,
                'fallback_type': 'emergency_fallback',
                'fallback_file': file_path,
                'user_message': 'Processing failed and recovery was not possible. Please try again.',
                'error_message': str(fallback_error),
                'is_recoverable': True
            }
    
    def validate_and_prepare_file(self, file_path: str) -> Dict[str, Any]:
        """Validate file and prepare for processing with error handling.
        
        Args:
            file_path: Path to the file to validate
            
        Returns:
            Dictionary with validation results and any error information
        """
        try:
            # Basic file validation
            self._validate_file(file_path)
            
            # Format validation
            format_validation = self.validate_format(file_path)
            
            return {
                'valid': True,
                'supported': format_validation['supported'],
                'format': format_validation.get('format', 'UNKNOWN'),
                'file_size': os.path.getsize(file_path),
                'error': None,
                'user_message': None
            }
            
        except Exception as e:
            error_type = self.fallback_handler._classify_error(e, file_path, 'validation')
            
            return {
                'valid': False,
                'supported': False,
                'format': 'UNKNOWN',
                'file_size': 0,
                'error': str(e),
                'user_message': self.fallback_handler.get_user_friendly_error_message(error_type),
                'suggested_action': self.fallback_handler.get_suggested_action(error_type),
                'is_recoverable': self.fallback_handler.is_error_recoverable(error_type)
            }
    
    def process_with_comprehensive_error_handling(self, file_path: str, 
                                                options: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process media with comprehensive error handling and user-friendly messages.
        
        Args:
            file_path: Path to the file to process
            options: Processing options
            
        Returns:
            Dictionary with processing results and error information
        """
        try:
            # Validate file first
            validation = self.validate_and_prepare_file(file_path)
            if not validation['valid']:
                return {
                    'success': False,
                    'result': None,
                    'error_type': 'validation_failed',
                    'user_message': validation['user_message'],
                    'suggested_action': validation.get('suggested_action', 'Please check the file and try again.'),
                    'is_recoverable': validation.get('is_recoverable', False)
                }
            
            # Process the media
            result = self.process_uploaded_media(file_path, options)
            
            return {
                'success': True,
                'result': result,
                'error_type': None,
                'user_message': 'Processing completed successfully.',
                'suggested_action': None,
                'is_recoverable': True,
                'fallback_applied': result.processing_status == 'completed_with_fallback'
            }
            
        except Exception as e:
            self.logger.error(f"Comprehensive processing failed: {str(e)}")
            
            error_info = self.handle_processing_error_with_fallback(
                file_path, e, 'comprehensive_processing'
            )
            
            return {
                'success': error_info['success'],
                'result': None,
                'error_type': type(e).__name__,
                'user_message': error_info['user_message'],
                'suggested_action': self.get_suggested_action(e, 'comprehensive_processing'),
                'is_recoverable': error_info['is_recoverable'],
                'fallback_applied': error_info['success'],
                'fallback_file': error_info.get('fallback_file')
            }