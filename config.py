import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

class Config:
    if os.getenv('GAE_ENV', '').startswith('standard'):
        db_pass = os.getenv('DB_PASSWORD')
        SQLALCHEMY_DATABASE_URI = f"postgresql+pg8000://postgres:{db_pass}@/cats?unix_sock=/cloudsql/eco-layout-442118-t8:us-central1:cats-db/.s.PGSQL.5432"
    else:
        SQLALCHEMY_DATABASE_URI = 'DATABASE_URL'

    # File storage configuration
    if os.getenv('GAE_ENV', '').startswith('standard'):
        STORAGE_BUCKET = "eco-layout-442118-t8-uploads"
        UPLOAD_FOLDER = '/tmp'  # Temporary storage
        CLOUD_STORAGE_URL = f"https://storage.googleapis.com/{STORAGE_BUCKET}"
    else:
        UPLOAD_FOLDER = 'catcare/static/uploads'
        CLOUD_STORAGE_URL = None


    # STATIC_FOLDER = os.path.join('catcare', 'static')
    # UPLOAD_FOLDER = os.path.join('catcare', 'static', 'uploads')

    SECRET_KEY=os.getenv('SECRET_KEY')
    JWT_SECRET_KEY=os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES=timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES=timedelta(days=30)
    JWT_ERROR_MESSAGE_KEY='error'
    JWT_TOKEN_LOCATION=['headers']
    JWT_HEADER_NAME='Authorization'
    JWT_HEADER_TYPE='Bearer'