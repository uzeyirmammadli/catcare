"""
Helper utilities for the application
"""

import os
import secrets
from math import radians, cos, sin, asin, sqrt
from typing import List, Dict, Any
from datetime import datetime
from flask import current_app


def generate_secure_filename(original_filename: str) -> str:
    """Generate a secure filename with timestamp and random string"""
    if not original_filename:
        return f"{secrets.token_hex(8)}.bin"

    # Get file extension
    name, ext = os.path.splitext(original_filename)
    if not ext:
        ext = ".bin"

    # Generate secure name
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    random_string = secrets.token_hex(8)

    return f"{timestamp}_{random_string}{ext}"


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))

    # Radius of earth in kilometers
    r = 6371
    return c * r


def paginate_query(query, page: int, per_page: int, max_per_page: int = 100):
    """Safely paginate a query with limits"""
    page = max(1, page)
    per_page = min(max_per_page, max(1, per_page))

    return query.paginate(page=page, per_page=per_page, error_out=False)


def sanitize_search_term(term: str) -> str:
    """Sanitize search terms to prevent SQL injection"""
    if not term:
        return ""

    # Remove special characters that could be used for SQL injection
    dangerous_chars = ["%", "_", ";", "--", "/*", "*/", "xp_", "sp_"]
    sanitized = term

    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")

    return sanitized.strip()


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def get_file_type(filename: str) -> str:
    """Get file type category from filename"""
    if not filename:
        return "unknown"

    ext = os.path.splitext(filename)[1].lower()

    image_exts = [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]
    video_exts = [".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm"]
    document_exts = [".pdf", ".doc", ".docx", ".txt", ".rtf"]

    if ext in image_exts:
        return "image"
    elif ext in video_exts:
        return "video"
    elif ext in document_exts:
        return "document"
    else:
        return "other"


def create_response(
    data: Any = None, message: str = None, status: int = 200, error: str = None
) -> Dict[str, Any]:
    """Create standardized API response"""
    response = {"success": status < 400, "status": status}

    if data is not None:
        response["data"] = data

    if message:
        response["message"] = message

    if error:
        response["error"] = error

    return response


def log_user_action(user_id: int, action: str, details: Dict[str, Any] = None):
    """Log user actions for audit trail"""
    log_data = {
        "user_id": user_id,
        "action": action,
        "timestamp": datetime.utcnow().isoformat(),
        "ip_address": getattr(current_app, "remote_addr", "unknown"),
    }

    if details:
        log_data["details"] = details

    current_app.logger.info(f"User action: {log_data}")


def is_safe_url(target: str) -> bool:
    """Check if a URL is safe for redirects"""
    if not target:
        return False

    # Basic checks for safe URLs
    if target.startswith("//") or target.startswith("http"):
        return False

    if any(char in target for char in ["<", ">", '"', "'"]):
        return False

    return True
