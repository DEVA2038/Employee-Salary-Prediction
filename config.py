# config.py
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent

# Database configuration
DATABASE_URL = "sqlite:///company_requests.db"

# Email configuration (UPDATE THESE WITH YOUR EMAIL or leave empty to disable)
# NOTE: Storing credentials in source code is NOT recommended for production.
# Prefer using environment variables: os.environ.get('SENDER_EMAIL') etc.
EMAIL_CONFIG = {
    'SMTP_SERVER': 'smtp.gmail.com',  # For Gmail
    'SMTP_PORT': 587,
    'SENDER_EMAIL': 'k.s.deva2038@gmail.com',  # admin / sender email
    'SENDER_PASSWORD': 'vutu yoff wvem yaix',  # admin password (IN PLAINTEXT — consider using env vars)
    'ADMIN_EMAIL': 'k.s.deva2038@gmail.com'  # admin notification recipient
}

# File upload configuration
UPLOAD_FOLDER = BASE_DIR / 'uploads'
COMPANY_MODELS_FOLDER = BASE_DIR / 'company_models'
ALLOWED_EXTENSIONS = {'csv'}

# Required dataset columns
REQUIRED_COLUMNS = [
    'age', 'experience', 'gender', 'role', 'sector', 
    'company', 'department', 'education', 'salary'
]
