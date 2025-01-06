import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
import logging
from flask_swagger_ui import get_swaggerui_blueprint
from flask_wtf.csrf import CSRFProtect
from config import Config
# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    basedir = os.path.abspath(os.path.dirname(__file__))    
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'main.login'

    if os.getenv('GAE_ENV', '').startswith('standard'):
        tmp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'uploads')
        os.makedirs(tmp_dir, exist_ok=True)
        app.config['UPLOAD_FOLDER'] = tmp_dir
    
    SWAGGER_URL = '/api/docs'
    API_URL = '/static/swagger.yaml'
    
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Cases Management API",
            'layout': 'BaseLayout',
            'deepLinking': True,
            'persistAuthorization': True,
            'displayRequestDuration': True,
            'docExpansion': 'list',
            'filter': True
        }
    )
    
    # Initialize database
    with app.app_context():
        try:
            from . import models
            db.create_all()
            logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"An error occurred during database initialization: {e}")
            raise
    
    # Register blueprints
    from .routes import main
    from .api import api
    
    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    
    
    # Ensure required directories exist
    # os.makedirs(os.path.join(basedir, 'static/uploads'), exist_ok=True)
    # os.makedirs(os.path.join(basedir, 'static'), exist_ok=True)
    if os.getenv('GAE_ENV', '').startswith('standard'):
        upload_dir = '/tmp/uploads'
    else:
        upload_dir = os.path.join(basedir, 'catcare/static/uploads')
    
    os.makedirs(upload_dir, exist_ok=True)
    app.config['UPLOAD_FOLDER'] = upload_dir
    
    # Copy swagger.yaml to static directory if it doesn't exist
    swagger_source = os.path.join(basedir, 'swagger.yaml')
    swagger_dest = os.path.join(basedir, 'static', 'swagger.yaml')
    
    if os.path.exists(swagger_source) and not os.path.exists(swagger_dest):
        import shutil
        shutil.copy2(swagger_source, swagger_dest)
    
    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has expired'}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {'error': 'Invalid token'}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {'error': 'Authorization token is missing'}, 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return {'error': 'Fresh token required'}, 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {'error': 'Token has been revoked'}, 401
    
    return app