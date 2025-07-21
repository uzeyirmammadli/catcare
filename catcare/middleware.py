"""
Middleware for request/response processing
"""

import time
import uuid
from flask import request, g, current_app
from functools import wraps


def setup_middleware(app):
    """Setup middleware for the application"""

    @app.before_request
    def before_request():
        """Execute before each request"""
        # Generate request ID for tracing
        g.request_id = str(uuid.uuid4())
        g.start_time = time.time()

        # Log request details
        current_app.logger.info(
            f"Request {g.request_id}: {request.method} {request.path}",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
                "user_agent": request.headers.get("User-Agent", ""),
            },
        )

    @app.after_request
    def after_request(response):
        """Execute after each request"""
        # Calculate request duration
        duration = time.time() - g.get("start_time", time.time())

        # Log response details
        current_app.logger.info(
            f"Response {g.get('request_id', 'unknown')}: {response.status_code} "
            f"({duration:.3f}s)",
            extra={
                "request_id": g.get("request_id", "unknown"),
                "status_code": response.status_code,
                "duration": duration,
            },
        )

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = g.get("request_id", "unknown")

        return response

    @app.errorhandler(400)
    def bad_request(error):
        """Handle bad request errors"""
        current_app.logger.warning(f"Bad request: {error}")
        return {
            "error": "Bad request",
            "message": (
                str(error.description) if hasattr(error, "description") else "Invalid request"
            ),
            "request_id": g.get("request_id", "unknown"),
        }, 400

    @app.errorhandler(401)
    def unauthorized(error):
        """Handle unauthorized errors"""
        return {
            "error": "Unauthorized",
            "message": "Authentication required",
            "request_id": g.get("request_id", "unknown"),
        }, 401

    @app.errorhandler(403)
    def forbidden(error):
        """Handle forbidden errors"""
        return {
            "error": "Forbidden",
            "message": "Access denied",
            "request_id": g.get("request_id", "unknown"),
        }, 403

    @app.errorhandler(404)
    def not_found(error):
        """Handle not found errors"""
        return {
            "error": "Not found",
            "message": "Resource not found",
            "request_id": g.get("request_id", "unknown"),
        }, 404

    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        """Handle rate limit errors"""
        return {
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "request_id": g.get("request_id", "unknown"),
        }, 429

    @app.errorhandler(500)
    def internal_error(error):
        """Handle internal server errors"""
        current_app.logger.error(f"Internal error: {error}", exc_info=True)
        return {
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "request_id": g.get("request_id", "unknown"),
        }, 500


def require_json(f):
    """Decorator to require JSON content type"""

    @wraps(f)
    def wrapper(*args, **kwargs):
        if not request.is_json:
            return {
                "error": "Content-Type must be application/json",
                "request_id": g.get("request_id", "unknown"),
            }, 400
        return f(*args, **kwargs)

    return wrapper
