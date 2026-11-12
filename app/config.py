import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    """การตั้งค่าพื้นฐานของ Typeclass Application"""
    SECRET_KEY = os.getenv("SECRET_KEY", "typeclass-super-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", SECRET_KEY)
    
    # Oracle Database Settings
    ORACLE_DB_USER = os.getenv("ORACLE_DB_USER")
    ORACLE_DB_PASSWORD = os.getenv("ORACLE_DB_PASSWORD")
    ORACLE_DB_DSN = os.getenv("ORACLE_DB_DSN")
    
    # Anti-cheat Thresholds
    MAX_WPM_THRESHOLD = int(os.getenv("MAX_WPM_THRESHOLD", "320"))

    # Google OAuth Settings
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

    # OCI Object Storage Settings
    OCI_STORAGE_PAR_URL = os.getenv("OCI_STORAGE_PAR_URL", "")
    OCI_PUBLIC_URL_PREFIX = os.getenv("OCI_PUBLIC_URL_PREFIX", "")
