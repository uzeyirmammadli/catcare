import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import logging
from .commands import register_commands

db = SQLAlchemy()
login_manager = LoginManager()
def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))

    app.config.update(
        SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:dominations@localhost:5432/cats',
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
        SECRET_KEY='GqOOhMcXCi0dH3a_sHdJgFBSu2ZnDbXHPoMlca4eGUI',
        DATABASE_PATH = os.path.join(basedir, 'cats.db'),
        UPLOAD_FOLDER = 'upload/photos'
    )

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    with app.app_context():
        try:
            from . import models
            db.create_all()
            logging.info("Database initialized successfully")
        except Exception as e:
            logging.error(f"An error occurred during database initialization: {e}")
            raise

        from .routes import main
        app.register_blueprint(main)
    register_commands(app)

    return app
