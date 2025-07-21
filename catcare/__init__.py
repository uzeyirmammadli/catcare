import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_jwt_extended import JWTManager
from flask_swagger_ui import get_swaggerui_blueprint
from flask_wtf.csrf import CSRFProtect
from flask_babel import Babel
from config import get_config

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
jwt = JWTManager()
csrf = CSRFProtect()
babel = Babel()


def create_app(config_name=None):
    app = Flask(__name__)

    # Load configuration
    if config_name:
        from config import config

        app.config.from_object(config[config_name])
    else:
        app.config.from_object(get_config())

    # Initialize configuration
    get_config().init_app(app)
    basedir = os.path.abspath(os.path.dirname(__file__))
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    jwt.init_app(app)
    # csrf.init_app(app)
    login_manager.login_view = "main.login"

    if os.getenv("GAE_ENV", "").startswith("standard"):
        tmp_dir = os.path.join(app.config["UPLOAD_FOLDER"], "uploads")
        os.makedirs(tmp_dir, exist_ok=True)
        app.config["UPLOAD_FOLDER"] = tmp_dir

    SWAGGER_URL = "/api/docs"
    API_URL = "/static/swagger.yaml"

    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            "app_name": "Cases Management API",
            "layout": "BaseLayout",
            "deepLinking": True,
            "persistAuthorization": True,
            "displayRequestDuration": True,
            "docExpansion": "list",
            "filter": True,
        },
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

    # Setup middleware
    from .middleware import setup_middleware

    setup_middleware(app)

    # Babel configuration - MUST be before template helpers
    app.config['LANGUAGES'] = {
        'en': 'English',
        'az': 'Azərbaycan dili'
    }
    app.config['BABEL_DEFAULT_LOCALE'] = 'en'
    app.config['BABEL_DEFAULT_TIMEZONE'] = 'UTC'
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'translations')

    def get_locale():
        try:
            from flask import request, session, has_request_context, g
            from flask_login import current_user
            
            # Only proceed if we have a request context
            if not has_request_context():
                return 'en'
            
            # Check if we've already determined the locale for this request
            if hasattr(g, 'locale'):
                return g.locale
            
            locale = 'en'  # default
            
            # 1. Check URL parameter first
            if request.args.get('lang') and request.args.get('lang') in app.config['LANGUAGES']:
                locale = request.args.get('lang')
                session['language'] = locale
            
            # 2. Check session
            elif 'language' in session and session['language'] in app.config['LANGUAGES']:
                locale = session['language']
            
            # 3. Check user preference (if logged in)
            elif current_user.is_authenticated and hasattr(current_user, 'language') and current_user.language:
                if current_user.language in app.config['LANGUAGES']:
                    locale = current_user.language
            
            # 4. Check browser preference
            else:
                browser_locale = request.accept_languages.best_match(app.config['LANGUAGES'].keys())
                if browser_locale:
                    locale = browser_locale
            
            # Cache the locale for this request
            g.locale = locale
            return locale
            
        except Exception as e:
            app.logger.debug(f'Locale selection error: {e}')
            return 'en'
    
    # Configure Babel with explicit settings
    babel.init_app(app, locale_selector=get_locale)
    
    # Ensure translations are loaded correctly
    @app.before_request
    def before_request():
        from flask import g
        from flask_babel import refresh
        # Force refresh of translations for each request
        refresh()

    # Initialize OAuth service
    from .services.oauth_service import oauth_service
    oauth_service.init_app(app)

    # Register template helpers - AFTER Babel is configured
    from .utils.template_helpers import safe_image_url, get_first_valid_image, format_file_size
    from flask_babel import get_locale, gettext, ngettext
    from .utils.i18n import translate_role, translate_status, translate_need, get_translation
    app.jinja_env.globals.update(
        safe_image_url=safe_image_url,
        get_first_valid_image=get_first_valid_image,
        format_file_size=format_file_size,
        oauth_service=oauth_service,
        get_locale=get_locale,
        _=gettext,
        _n=ngettext,
        translate_role=translate_role,
        translate_status=translate_status,
        translate_need=translate_need,
        get_translation=get_translation
    )

    # Register blueprints
    from .routes import main
    from .api import api

    app.register_blueprint(main)
    app.register_blueprint(api)
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)

    # Ensure required directories exist
    # os.makedirs(os.path.join(basedir, 'static/uploads'), exist_ok=True)
    # os.makedirs(os.path.join(basedir, 'static'), exist_ok=True)
    if os.getenv("GAE_ENV", "").startswith("standard"):
        upload_dir = "/tmp/uploads"
    else:
        upload_dir = os.path.join(basedir, "catcare/static/uploads")

    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_dir

    # Copy swagger.yaml to static directory if it doesn't exist
    swagger_source = os.path.join(basedir, "swagger.yaml")
    swagger_dest = os.path.join(basedir, "static", "swagger.yaml")

    if os.path.exists(swagger_source) and not os.path.exists(swagger_dest):
        import shutil

        shutil.copy2(swagger_source, swagger_dest)

    # JWT error handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"error": "Token has expired"}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"error": "Invalid token"}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"error": "Authorization token is missing"}, 401

    @jwt.needs_fresh_token_loader
    def token_not_fresh_callback(jwt_header, jwt_payload):
        return {"error": "Fresh token required"}, 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return {"error": "Token has been revoked"}, 401

    return app
