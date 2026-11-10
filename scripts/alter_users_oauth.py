"""
สคริปต์สำหรับเพิ่มคอลัมน์ GOOGLE_ID และ AUTH_PROVIDER ในตาราง U.USERS สำหรับ Google OAuth 2.0
หมายเหตุ: ต้องรันด้วยบัญชีเจ้าของ Schema (U หรือ ADMIN) ที่มีสิทธิ์ ALTER TABLE
"""
import os
import sys
import oracledb
from dotenv import load_dotenv

load_dotenv(override=True)

DSN = os.getenv("ORACLE_DB_DSN")
USER = sys.argv[1] if len(sys.argv) > 1 else os.getenv("ORACLE_DB_ADMIN_USER", os.getenv("ORACLE_DB_USER"))
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else os.getenv("ORACLE_DB_ADMIN_PASSWORD", os.getenv("ORACLE_DB_PASSWORD"))

SQL_STATEMENTS = [
    "ALTER TABLE U.USERS ADD (GOOGLE_ID VARCHAR2(255))",
    "ALTER TABLE U.USERS ADD (AUTH_PROVIDER VARCHAR2(50) DEFAULT 'LOCAL')",
    "ALTER TABLE U.USERS ADD CONSTRAINT UQ_USERS_GOOGLE_ID UNIQUE (GOOGLE_ID)",
    "ALTER TABLE U.USERS ADD (FIRST_NAME VARCHAR2(100))",
    "ALTER TABLE U.USERS ADD (LAST_NAME VARCHAR2(100))",
    """
    UPDATE U.USERS
    SET FIRST_NAME = CASE
            WHEN INSTR(TRIM(FULL_NAME), ' ') > 0
            THEN SUBSTR(TRIM(FULL_NAME), 1, INSTR(TRIM(FULL_NAME), ' ') - 1)
            ELSE TRIM(FULL_NAME)
        END,
        LAST_NAME = CASE
            WHEN INSTR(TRIM(FULL_NAME), ' ') > 0
            THEN TRIM(SUBSTR(TRIM(FULL_NAME), INSTR(TRIM(FULL_NAME), ' ') + 1))
            ELSE ''
        END
    WHERE FIRST_NAME IS NULL
    """,
    "ALTER TABLE U.CLASSROOMS ADD (STATUS VARCHAR2(20) DEFAULT 'closed')",
    "ALTER TABLE U.CLASSROOMS ADD (DURATION NUMBER DEFAULT 60)",
    "UPDATE U.CLASSROOMS SET STATUS = NVL(STATUS, 'closed'), DURATION = NVL(DURATION, 60)",
]


def migrate():
    print(f"กำลังเชื่อมต่อ Oracle DB ด้วยผู้ใช้: {USER} ...")
    conn = oracledb.connect(user=USER, password=PASSWORD, dsn=DSN)
    try:
        with conn.cursor() as cur:
            for sql in SQL_STATEMENTS:
                try:
                    cur.execute(sql)
                    print(f"✅ สำเร็จ: {sql}")
                except oracledb.Error as err:
                    print(f"⚠️ ข้าม/แจ้งเตือน ({sql}): {err}")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()

