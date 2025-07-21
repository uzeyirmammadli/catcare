"""
OAuth integration service for Google and Facebook authentication
"""
import requests
from flask import current_app, session, request, url_for, redirect, flash
from authlib.integrations.flask_client import OAuth
from .auth_service import AuthService
from ..models import User, db


class OAuthService:
    """Service class for OAuth operations"""
    
    def __init__(self, app=None):
        self.oauth = OAuth()
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize OAuth with Flask app"""
        self.oauth.init_app(app)
        
        # Initialize OAuth providers only if credentials are configured
        self.google = None
        self.facebook = None
        
        # Google OAuth
        if app.config.get('GOOGLE_CLIENT_ID') and app.config.get('GOOGLE_CLIENT_SECRET'):
            try:
                self.google = self.oauth.register(
                    name='google',
                    client_id=app.config.get('GOOGLE_CLIENT_ID'),
                    client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
                    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
                    client_kwargs={
                        'scope': 'openid email profile'
                    }
                )
            except Exception as e:
                app.logger.warning(f"Failed to initialize Google OAuth: {str(e)}")
        
        # Facebook OAuth
        if app.config.get('FACEBOOK_CLIENT_ID') and app.config.get('FACEBOOK_CLIENT_SECRET'):
            try:
                self.facebook = self.oauth.register(
                    name='facebook',
                    client_id=app.config.get('FACEBOOK_CLIENT_ID'),
                    client_secret=app.config.get('FACEBOOK_CLIENT_SECRET'),
                    access_token_url='https://graph.facebook.com/oauth/access_token',
                    authorize_url='https://www.facebook.com/dialog/oauth',
                    api_base_url='https://graph.facebook.com/',
                    client_kwargs={'scope': 'email'},
                )
            except Exception as e:
                app.logger.warning(f"Failed to initialize Facebook OAuth: {str(e)}")
    
    def get_google_auth_url(self):
        """Get Google OAuth authorization URL"""
        if not self.google:
            flash('Google OAuth is not configured.', 'error')
            return redirect(url_for('main.login'))
        
        redirect_uri = url_for('main.oauth_callback', provider='google', _external=True)
        return self.google.authorize_redirect(redirect_uri)
    
    def get_facebook_auth_url(self):
        """Get Facebook OAuth authorization URL"""
        if not self.facebook:
            flash('Facebook OAuth is not configured.', 'error')
            return redirect(url_for('main.login'))
        
        redirect_uri = url_for('main.oauth_callback', provider='facebook', _external=True)
        return self.facebook.authorize_redirect(redirect_uri)
    
    def handle_google_callback(self):
        """Handle Google OAuth callback"""
        if not self.google:
            return None
            
        try:
            token = self.google.authorize_access_token()
            user_info = token.get('userinfo')
            
            if user_info:
                user = AuthService.create_oauth_user(
                    provider='google',
                    oauth_id=user_info['sub'],
                    email=user_info['email'],
                    first_name=user_info.get('given_name'),
                    last_name=user_info.get('family_name')
                )
                return user
            
        except Exception as e:
            current_app.logger.error(f"Google OAuth error: {str(e)}")
            
        return None
    
    def handle_facebook_callback(self):
        """Handle Facebook OAuth callback"""
        if not self.facebook:
            return None
            
        try:
            token = self.facebook.authorize_access_token()
            
            # Get user info from Facebook
            resp = self.facebook.get('me?fields=id,email,first_name,last_name', token=token)
            user_info = resp.json()
            
            if user_info and 'id' in user_info:
                user = AuthService.create_oauth_user(
                    provider='facebook',
                    oauth_id=user_info['id'],
                    email=user_info.get('email'),
                    first_name=user_info.get('first_name'),
                    last_name=user_info.get('last_name')
                )
                return user
            
        except Exception as e:
            current_app.logger.error(f"Facebook OAuth error: {str(e)}")
            
        return None
    
    def unlink_oauth_account(self, user, provider):
        """Unlink OAuth account from user"""
        if user.oauth_provider == provider:
            user.oauth_provider = None
            user.oauth_id = None
            db.session.commit()
            return True
        return False
    
    def is_google_available(self):
        """Check if Google OAuth is available"""
        return self.google is not None
    
    def is_facebook_available(self):
        """Check if Facebook OAuth is available"""
        return self.facebook is not None
    
    def has_oauth_providers(self):
        """Check if any OAuth providers are available"""
        return self.is_google_available() or self.is_facebook_available()


# Global OAuth service instance
oauth_service = OAuthService()