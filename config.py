import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS=False
    SECRET_KEY=os.getenv('SECRET_KEY')
    UPLOAD_FOLDER = os.path.join('catcare', 'static', 'uploads')
    JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30)
    JWT_ERROR_MESSAGE_KEY='error'
    JWT_TOKEN_LOCATION=['headers']
    JWT_HEADER_NAME='Authorization'
    JWT_HEADER_TYPE='Bearer'