"""
Configuration module.

Centralises every env-driven setting so the rest of the app can stay
clean. Reads from environment variables (or a .env file in development).
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if it exists (silently ignored otherwise).
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / '.env')


class Config:
    # ---- Flask ----
    SECRET_KEY = os.getenv('SECRET_KEY', 'autoreport-ai-dev-secret')

    # ---- File storage ----
    UPLOAD_FOLDER = str(BASE_DIR / 'uploads')
    REPORT_FOLDER = str(BASE_DIR / 'reports')

    # Allowed extensions for dataset uploads.
    ALLOWED_EXTENSIONS = {'.csv', '.xlsx', '.xls'}

    # ---- Database (MySQL) ----
    # The connection URI is optional — if absent we fall back to a local
    # SQLite DB so the project still runs out of the box for development.
    MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.getenv('MYSQL_PORT', 3306))
    MYSQL_USER = os.getenv('MYSQL_USER', '')
    MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
    MYSQL_DB = os.getenv('MYSQL_DB', 'autoreport_ai')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@"
        f"{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
        if MYSQL_USER
        else f"sqlite:///{BASE_DIR / 'autoreport.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---- OpenAI ----
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

    # ---- Misc ----
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB upload cap