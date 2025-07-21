"""
Template helper functions for better performance
"""

import os
from flask import current_app, url_for


def safe_image_url(image_url, placeholder="/static/placeholder.jpg"):
    """
    Return image URL if file exists, otherwise return placeholder
    """
    if not image_url:
        return placeholder
    
    # For local files, check if they exist
    if image_url.startswith('/uploads/'):
        file_path = os.path.join(current_app.root_path, 'static', image_url.lstrip('/'))
        if not os.path.exists(file_path):
            return placeholder
    
    return image_url


def get_first_valid_image(image_list, placeholder="/static/placeholder.jpg"):
    """
    Get the first valid image from a list, or return placeholder
    """
    if not image_list:
        return placeholder
    
    for image_url in image_list:
        if image_url.startswith('/uploads/'):
            file_path = os.path.join(current_app.root_path, 'static', image_url.lstrip('/'))
            if os.path.exists(file_path):
                return image_url
        else:
            # For cloud URLs, assume they exist
            return image_url
    
    return placeholder


def format_file_size(size_bytes):
    """Format file size in human readable format"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"