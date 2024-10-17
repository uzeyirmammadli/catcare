import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config.update(
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'cats.db'),
        SQLALCHEMY_TRACK_MODIFICATIONS = False,
        SECRET_KEY='GqOOhMcXCi0dH3a_sHdJgFBSu2ZnDbXHPoMlca4eGUI',
        DATABASE_PATH = os.path.join(basedir, 'cats.db')
    )

    # db_path = os.path.join(app.root_path, 'cats.db')
    # print(f"Database path: {db_path}")
    # app.config.update(
    #     SQLALCHEMY_DATABASE_URI='sqlite:///cats.db',
    #     SQLALCHEMY_TRACK_MODIFICATIONS=False,
    #     SECRET_KEY='GqOOhMcXCi0dH3a_sHdJgFBSu2ZnDbXHPoMlca4eGUI',
    #     DATABASE_PATH='cats.db'
    # )
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.login'

    with app.app_context():
        from . import sqlite_memory
        try:
            sqlite_memory.initialize(app.config['DATABASE_PATH'])
            sqlite_memory.create_test_user(app.config['DATABASE_PATH'])
        except Exception as e:
            print(f"An error occurred during database initialization: {e}")

        from . import models
        db.create_all()

        from .routes import main
        app.register_blueprint(main)

    return app
