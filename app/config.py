import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """การตั้งค่าพื้นฐานของ Typeclass Application"""
    SECRET_KEY = os.getenv("SECRET_KEY", "typeclass-super-secret-key")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "typeclass-jwt-secret-key")
    
    # Oracle Database Settings
    ORACLE_DB_USER = os.getenv("ORACLE_DB_USER")
    ORACLE_DB_PASSWORD = os.getenv("ORACLE_DB_PASSWORD")
    ORACLE_DB_DSN = os.getenv("ORACLE_DB_DSN")
    
    # Anti-cheat Thresholds
    MAX_WPM_THRESHOLD = int(os.getenv("MAX_WPM_THRESHOLD", "320"))
