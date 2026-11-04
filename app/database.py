import os
import oracledb
from dotenv import load_dotenv

# โหลดค่าตัวแปรจากไฟล์ .env
load_dotenv()

DB_USER = os.getenv("ORACLE_DB_USER")
DB_PASSWORD = os.getenv("ORACLE_DB_PASSWORD")
CONNECT_STRING = os.getenv("ORACLE_DB_DSN")

def get_db_connection():
    """
    ฟังก์ชันสำหรับสร้างการเชื่อมต่อกับ Oracle Database 
    เรียกใช้ฟังก์ชันนี้เมื่อต้องการ Insert/Select ข้อมูล
    """
    try:
        # สร้างการเชื่อมต่อแบบ Direct Connection (รองรับ Thin Mode)
        connection = oracledb.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            dsn=CONNECT_STRING
        )
        print("✅ [Database] Connected successfully!")
        return connection
    except oracledb.Error as e:
        print(f"❌ [Database] Could not connect to the database - Error: {e}")
        return None

# --- ส่วนสำหรับการทดสอบรันไฟล์นี้โดยตรง ---
if __name__ == "__main__":
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM DUAL")
            result = cursor.fetchone()
            print(f"Query result (DUAL): {result[0]}")
        finally:
            cursor.close()
            conn.close()