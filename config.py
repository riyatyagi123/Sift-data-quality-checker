import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'sift-validator-secret-key-12345')
    
    # Base workspace directory
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    # Upload and processing folders
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    PROCESSED_FOLDER = os.path.join(BASE_DIR, 'processed')
    CHUNKS_FOLDER = os.path.join(BASE_DIR, 'chunks')
    
    # File limits
    ALLOWED_EXTENSIONS = {'csv'}
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
    
    # Max rows for preview
    PREVIEW_ROWS = 10
