"""
Custom decorators for the application
"""

import functools
from flask import jsonify, request, current_app
from flask_login import current_user
from datetime import datetime, timedelta
from collections import defaultdict


# Rate limiting storage (in production, use Redis)
rate_limit_storage = defaultdict(list)


def rate_limit(max_requests: int = 100, window_minutes: int = 60):
    """Rate limiting decorator"""

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            # Get client identifier
            client_id = request.remote_addr
            if current_user.is_authenticated:
                client_id = f"user_{current_user.id}"

            now = datetime.utcnow()
            window_start = now - timedelta(minutes=window_minutes)

            # Clean old requests
            rate_limit_storage[client_id] = [
                req_time for req_time in rate_limit_storage[client_id] if req_time > window_start
            ]

            # Check rate limit
            if len(rate_limit_storage[client_id]) >= max_requests:
                return (
                    jsonify({"error": "Rate limit exceeded", "retry_after": window_minutes * 60}),
                    429,
                )

            # Add current request
            rate_limit_storage[client_id].append(now)

            return f(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(f):
    """Decorator to require admin privileges"""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Authentication required"}), 401

        # Add admin check logic here when you implement user roles
        # For now, just check if user exists
        if not current_user:
            return jsonify({"error": "Admin privileges required"}), 403

        return f(*args, **kwargs)

    return wrapper


def validate_json(required_fields: list = None):
    """Decorator to validate JSON input"""

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                return jsonify({"error": "Content-Type must be application/json"}), 400

            data = request.get_json()
            if not data:
                return jsonify({"error": "Invalid JSON data"}), 400

            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    return (
                        jsonify(
                            {"error": "Missing required fields", "missing_fields": missing_fields}
                        ),
                        400,
                    )

            return f(*args, **kwargs)

        return wrapper

    return decorator


def handle_errors(f):
    """Decorator to handle common errors"""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.error(f"ValueError in {f.__name__}: {e}")
            return jsonify({"error": str(e)}), 400
        except PermissionError as e:
            current_app.logger.error(f"PermissionError in {f.__name__}: {e}")
            return jsonify({"error": "Permission denied"}), 403
        except Exception as e:
            current_app.logger.error(f"Unexpected error in {f.__name__}: {e}")
            return jsonify({"error": "Internal server error"}), 500

    return wrapper
