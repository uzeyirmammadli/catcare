import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration class"""
    
    # Security
    SECRET_KEY = os.getenv('SECRET_KEY') or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY') or 'jwt-secret-key-change-in-production'
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ERROR_MESSAGE_KEY = 'error'
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # File Upload
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    ALLOWED_VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.webm']
    ALLOWED_DOCUMENT_EXTENSIONS = ['.pdf']
    
    # Pagination
    CASES_PER_PAGE = 10
    MAX_CASES_PER_PAGE = 100
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.getenv('REDIS_URL', 'memory://')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        pass


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///catcare_dev.db')
    UPLOAD_FOLDER = 'catcare/static/uploads'
    CLOUD_STORAGE_URL = None
    
    # Development-specific settings
    WTF_CSRF_ENABLED = False  # Disable CSRF for development
    TESTING = False


class ProductionConfig(Config):
    """Production configuration for Google App Engine"""
    DEBUG = False
    TESTING = False
    
    # Database configuration for Cloud SQL
    db_pass = os.getenv('DB_PASSWORD')
    if not db_pass:
        raise ValueError("DB_PASSWORD environment variable is required in production")
    
    # Cloud SQL instance connection
    cloud_sql_instance = os.getenv('CLOUD_SQL_INSTANCE')
    if not cloud_sql_instance:
        raise ValueError("CLOUD_SQL_INSTANCE environment variable is required in production")
    
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+pg8000://postgres:{db_pass}@/cats"
        f"?unix_sock=/cloudsql/{cloud_sql_instance}/.s.PGSQL.5432"
    )
    
    # Cloud Storage configuration
    STORAGE_BUCKET = os.getenv('STORAGE_BUCKET')
    if not STORAGE_BUCKET:
        raise ValueError("STORAGE_BUCKET environment variable is required in production")
    UPLOAD_FOLDER = '/tmp'
    CLOUD_STORAGE_URL = f"https://storage.googleapis.com/{STORAGE_BUCKET}"
    
    # Security settings
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    @staticmethod
    def init_app(app):
        Config.init_app(app)
        
        # Log to stderr in production
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    UPLOAD_FOLDER = '/tmp/test_uploads'


# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    if os.getenv('GAE_ENV', '').startswith('standard'):
        env = 'production'
    
    return config.get(env, config['default'])