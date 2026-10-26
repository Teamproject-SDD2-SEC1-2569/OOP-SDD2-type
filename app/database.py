import os
import oracledb
from dotenv import load_dotenv

load_dotenv()


def get_db_connection():
    """สร้างการเชื่อมต่อ Oracle Database"""
    return oracledb.connect(
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        dsn=os.getenv("DB_DSN")
    )