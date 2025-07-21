"""
Input validation utilities
"""

import re
from typing import List, Dict, Any, Optional
from werkzeug.datastructures import FileStorage


class ValidationError(Exception):
    """Custom validation error"""

    pass


class InputValidator:
    """Input validation utilities"""

    @staticmethod
    def validate_location(location: str) -> str:
        """Validate location input"""
        if not location or not location.strip():
            raise ValidationError("Location is required")

        location = location.strip()
        if len(location) < 2:
            raise ValidationError("Location must be at least 2 characters")
        if len(location) > 500:
            raise ValidationError("Location must be less than 500 characters")

        return location

    @staticmethod
    def validate_coordinates(latitude: Optional[float], longitude: Optional[float]) -> tuple:
        """Validate latitude and longitude"""
        if latitude is not None:
            if not -90 <= latitude <= 90:
                raise ValidationError("Latitude must be between -90 and 90")

        if longitude is not None:
            if not -180 <= longitude <= 180:
                raise ValidationError("Longitude must be between -180 and 180")

        return latitude, longitude

    @staticmethod
    def validate_needs(needs: List[str]) -> List[str]:
        """Validate needs list"""
        if not needs:
            return []

        valid_needs = []
        allowed_needs = [
            "Food",
            "Water",
            "Medicine",
            "Shelter",
            "Veterinary Care",
            "Rescue",
            "Adoption",
            "Spay/Neuter",
            "Other",
        ]

        for need in needs:
            if need.strip() in allowed_needs:
                valid_needs.append(need.strip())

        return valid_needs

    @staticmethod
    def validate_status(status: str) -> str:
        """Validate case status"""
        if status not in ["OPEN", "RESOLVED"]:
            raise ValidationError("Status must be 'OPEN' or 'RESOLVED'")
        return status.upper()

    @staticmethod
    def validate_file(
        file: FileStorage, allowed_extensions: List[str], max_size_mb: int = 10
    ) -> bool:
        """Validate uploaded file"""
        if not file or not file.filename:
            return False

        # Check file extension
        if not any(file.filename.lower().endswith(ext) for ext in allowed_extensions):
            raise ValidationError(
                f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
            )

        # Check file size (approximate)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset to beginning

        if size > max_size_mb * 1024 * 1024:
            raise ValidationError(f"File size must be less than {max_size_mb}MB")

        return True

    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email format"""
        if not email:
            raise ValidationError("Email is required")

        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, email):
            raise ValidationError("Invalid email format")

        return email.lower().strip()

    @staticmethod
    def validate_username(username: str) -> str:
        """Validate username"""
        if not username:
            raise ValidationError("Username is required")

        username = username.strip()
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters")
        if len(username) > 50:
            raise ValidationError("Username must be less than 50 characters")

        if not re.match(r"^[a-zA-Z0-9_]+$", username):
            raise ValidationError("Username can only contain letters, numbers, and underscores")

        return username

    @staticmethod
    def validate_password(password: str) -> str:
        """Validate password strength"""
        if not password:
            raise ValidationError("Password is required")

        if len(password) < 6:
            raise ValidationError("Password must be at least 6 characters")

        if len(password) > 128:
            raise ValidationError("Password must be less than 128 characters")

        # Check for at least one letter and one number
        if not re.search(r"[a-zA-Z]", password):
            raise ValidationError("Password must contain at least one letter")

        if not re.search(r"\d", password):
            raise ValidationError("Password must contain at least one number")

        return password
