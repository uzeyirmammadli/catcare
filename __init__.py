import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
import logging
from flask_swagger_ui import get_swaggerui_blueprint
from .commands import register_commands
from datetime import timedelta

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    
    # Configure base directory
    basedir = os.path.abspath(os.path.dirname(__file__))
    
    # Application configuration
    app.config.update(
        SQLALCHEMY_DATABASE_URI='postgresql://postgres:dominations@localhost:5432/cats',
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY='GqOOhMcXCi0dH3a_sHdJgFBSu2ZnDbXHPoMlca4eGUI',
        DATABASE_PATH=os.path.join(basedir, 'cats.db'),
        UPLOAD_FOLDER='static/uploads',
        # JWT Configuration
        JWT_SECRET_KEY='94017f281a5aa2fc127dc9f2a7f54abe077a8268f2dcd6cbadc7be499ae6ddce',
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1),
        JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30),
        JWT_ERROR_MESSAGE_KEY='error',
        JWT_TOKEN_LOCATION=['headers'],
        JWT_HEADER_NAME='Authorization',
        JWT_HEADER_TYPE='Bearer'
    )
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)
    login_manager.login_view = 'main.login'
    
    # Configure Swagger UI
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
    
    # Register CLI commands
    register_commands(app)
    
    # Ensure required directories exist
    os.makedirs(os.path.join(basedir, 'static/uploads'), exist_ok=True)
    os.makedirs(os.path.join(basedir, 'static'), exist_ok=True)
    
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