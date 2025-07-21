"""
Authentication service for advanced authentication features
"""
import jwt
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import current_app, request, jsonify, session, flash, redirect, url_for
from flask_login import current_user
from ..models import User, db


class AuthService:
    """Service class for authentication operations"""
    
    @staticmethod
    def generate_jwt_token(user_id, expires_delta=None):
        """Generate JWT access token"""
        if expires_delta is None:
            expires_delta = timedelta(hours=1)
        
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + expires_delta,
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(
            payload,
            current_app.config.get('SECRET_KEY'),
            algorithm='HS256'
        )
    
    @staticmethod
    def verify_jwt_token(token):
        """Verify JWT token and return user_id"""
        try:
            payload = jwt.decode(
                token,
                current_app.config.get('SECRET_KEY'),
                algorithms=['HS256']
            )
            return payload['user_id']
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
    
    @staticmethod
    def refresh_jwt_token(refresh_token):
        """Refresh JWT token using refresh token"""
        user = User.query.filter_by(jwt_refresh_token=refresh_token).first()
        
        if not user or not user.is_jwt_refresh_valid():
            return None, None
        
        # Generate new tokens
        access_token = AuthService.generate_jwt_token(user.id)
        new_refresh_token = user.generate_jwt_refresh_token()
        
        db.session.commit()
        
        return access_token, new_refresh_token
    
    @staticmethod
    def send_verification_email(user):
        """Send verification email to user"""
        # This would integrate with your email service
        # For now, just generate the token
        token = user.generate_verification_token()
        db.session.commit()
        
        # In a real implementation, you would send an email here
        verification_url = url_for('main.verify_email', token=token, _external=True)
        
        # Log for development
        current_app.logger.info(f"Verification URL for {user.email}: {verification_url}")
        
        return token
    
    @staticmethod
    def create_oauth_user(provider, oauth_id, email, first_name=None, last_name=None):
        """Create user from OAuth provider"""
        # Check if user already exists
        user = User.query.filter_by(oauth_provider=provider, oauth_id=oauth_id).first()
        
        if user:
            user.update_last_login()
            db.session.commit()
            return user
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            # Link OAuth to existing account
            existing_user.oauth_provider = provider
            existing_user.oauth_id = oauth_id
            existing_user.update_last_login()
            db.session.commit()
            return existing_user
        
        # Create new user
        username = email.split('@')[0]
        counter = 1
        original_username = username
        
        # Ensure unique username
        while User.query.filter_by(username=username).first():
            username = f"{original_username}{counter}"
            counter += 1
        
        user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            oauth_provider=provider,
            oauth_id=oauth_id,
            is_verified=True,  # OAuth users are pre-verified
            role='REPORTER'  # Default role
        )
        
        user.update_last_login()
        db.session.add(user)
        db.session.commit()
        
        return user


# Role-based access control decorators
def require_role(required_role):
    """Decorator to require specific role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'error')
                return redirect(url_for('main.login'))
            
            if not current_user.has_role(required_role):
                flash('You do not have permission to access this page.', 'error')
                return redirect(url_for('main.homepage'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_admin(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('main.login'))
        
        if not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('main.homepage'))
        
        return f(*args, **kwargs)
    return decorated_function


def require_volunteer_or_admin(f):
    """Decorator to require volunteer or admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('main.login'))
        
        if not (current_user.is_volunteer() or current_user.is_admin()):
            flash('Volunteer or admin access required.', 'error')
            return redirect(url_for('main.homepage'))
        
        return f(*args, **kwargs)
    return decorated_function


def require_verified_account(f):
    """Decorator to require verified account"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('main.login'))
        
        if not current_user.is_verified:
            flash('Please verify your email address to access this feature.', 'warning')
            return redirect(url_for('main.profile'))
        
        return f(*args, **kwargs)
    return decorated_function


# JWT API decorators
def jwt_required(f):
    """Decorator for JWT token authentication in API endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            user_id = AuthService.verify_jwt_token(token)
            if not user_id:
                return jsonify({'error': 'Token is invalid or expired'}), 401
            
            # Add user to request context
            request.current_user_id = user_id
            
        except Exception as e:
            return jsonify({'error': 'Token verification failed'}), 401
        
        return f(*args, **kwargs)
    return decorated_function


def api_require_role(required_role):
    """Decorator to require specific role for API endpoints"""
    def decorator(f):
        @wraps(f)
        @jwt_required
        def decorated_function(*args, **kwargs):
            user = User.query.get(request.current_user_id)
            if not user or not user.has_role(required_role):
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator