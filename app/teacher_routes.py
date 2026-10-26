import secrets

from flask import Blueprint, request, jsonify
from flask_jwt_extended import get_jwt_identity

from .auth_utils import require_role
from .database import get_db_connection


teacher_bp = Blueprint("teacher", __name__)

# เก็บสถานะและระยะเวลาของห้องไว้ชั่วคราวในหน่วยความจำ
# เนื่องจากตาราง CLASSROOMS ยังไม่มีคอลัมน์ STATUS และ DURATION
# ข้อมูลส่วนนี้จะหายไปเมื่อรีสตาร์ตแอปพลิเคชัน
room_settings = {}


def generate_room_code(cursor):
    """สร้างรหัสห้องที่ไม่ซ้ำกับข้อมูลใน Oracle"""

    while True:
        room_code = secrets.token_hex(3).upper()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM U.CLASSROOMS
            WHERE ROOM_CODE = :room_code
            """,
            {"room_code": room_code}
        )

        if cursor.fetchone()[0] == 0:
            return room_code


def get_current_teacher(cursor):
    """ดึง TEACHER_ID ของครูที่เข้าสู่ระบบอยู่"""

    identity = get_jwt_identity()

    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return None

    cursor.execute(
        """
        SELECT TEACHER_ID
        FROM U.TEACHERS
        WHERE TEACHER_ID = :user_id
        """,
        {"user_id": user_id}
    )

    result = cursor.fetchone()

    return result[0] if result else None


def get_room_settings(room_code):
    """ดึงสถานะและระยะเวลาของห้องจากหน่วยความจำ"""

    return room_settings.get(
        room_code,
        {
            "duration": None,
            "status": "closed"
        }
    )


# ==================================================
# 1. สร้างห้องเรียน
# POST /api/teacher/rooms
# ==================================================

@teacher_bp.route("/rooms", methods=["POST"])
@require_role("Teacher")
def create_room():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "กรุณาส่งข้อมูล JSON"
        }), 400

    room_name = data.get("room_name")
    duration = data.get("duration")

    if not isinstance(room_name, str) or not room_name.strip():
        return jsonify({
            "error": "กรุณาระบุชื่อห้องเรียน"
        }), 400

    room_name = room_name.strip()

    if len(room_name) > 100:
        return jsonify({
            "error": "ชื่อห้องเรียนต้องไม่เกิน 100 ตัวอักษร"
        }), 400

    if type(duration) is not int or duration not in (30, 60):
        return jsonify({
            "error": "ระยะเวลาต้องเป็น 30 หรือ 60 วินาที"
        }), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        teacher_id = get_current_teacher(cursor)

        if teacher_id is None:
            return jsonify({
                "error": "ไม่พบข้อมูลครูสำหรับบัญชีนี้"
            }), 403

        room_code = generate_room_code(cursor)

        classroom_id_var = cursor.var(int)

        cursor.execute(
            """
            INSERT INTO U.CLASSROOMS
                (ROOM_NAME, ROOM_CODE, TEACHER_ID)
            VALUES
                (:room_name, :room_code, :teacher_id)
            RETURNING CLASSROOM_ID INTO :classroom_id
            """,
            {
                "room_name": room_name,
                "room_code": room_code,
                "teacher_id": teacher_id,
                "classroom_id": classroom_id_var
            }
        )

        classroom_id = classroom_id_var.getvalue()

        if isinstance(classroom_id, list):
            classroom_id = classroom_id[0]

        conn.commit()

        # เก็บข้อมูลที่ตาราง Oracle ยังไม่มีคอลัมน์รองรับ
        room_settings[room_code] = {
            "duration": duration,
            "status": "closed"
        }

        return jsonify({
            "message": "สร้างห้องเรียนสำเร็จ",
            "room": {
                "classroom_id": classroom_id,
                "room_name": room_name,
                "room_code": room_code,
                "teacher_id": teacher_id,
                "duration": duration,
                "status": "closed"
            },
            "notice": (
                "ชื่อห้องและรหัสห้องบันทึกลง Oracle แล้ว "
                "ส่วน duration และ status เก็บไว้ชั่วคราวในหน่วยความจำ"
            )
        }), 201

    except Exception:
        if conn:
            conn.rollback()

        return jsonify({
            "error": "สร้างห้องเรียนไม่สำเร็จ"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==================================================
# 2. ดูรายการห้องเรียนของครู
# GET /api/teacher/rooms
# ==================================================

@teacher_bp.route("/rooms", methods=["GET"])
@require_role("Teacher")
def list_rooms():

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        teacher_id = get_current_teacher(cursor)

        if teacher_id is None:
            return jsonify({
                "error": "ไม่พบข้อมูลครู"
            }), 403

        cursor.execute(
            """
            SELECT
                CLASSROOM_ID,
                ROOM_NAME,
                ROOM_CODE,
                TEACHER_ID,
                CREATED_AT
            FROM U.CLASSROOMS
            WHERE TEACHER_ID = :teacher_id
            ORDER BY CLASSROOM_ID DESC
            """,
            {"teacher_id": teacher_id}
        )

        rooms = []

        for row in cursor.fetchall():

            room_code = row[2]
            settings = get_room_settings(room_code)

            rooms.append({
                "classroom_id": row[0],
                "room_name": row[1],
                "room_code": room_code,
                "teacher_id": row[3],
                "created_at": (
                    row[4].isoformat() if row[4] else None
                ),
                "duration": settings["duration"],
                "status": settings["status"]
            })

        return jsonify({
            "rooms": rooms
        }), 200

    except Exception:
        return jsonify({
            "error": "ไม่สามารถดึงข้อมูลห้องเรียนได้"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==================================================
# 3. เปิดหรือปิดห้องเรียน
# PATCH /api/teacher/rooms/<room_code>/status
# ==================================================

@teacher_bp.route(
    "/rooms/<room_code>/status",
    methods=["PATCH"]
)
@require_role("Teacher")
def update_room_status(room_code):

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "กรุณาส่งข้อมูล JSON"
        }), 400

    status = data.get("status")

    if status not in ("open", "closed"):
        return jsonify({
            "error": "สถานะต้องเป็น open หรือ closed"
        }), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        teacher_id = get_current_teacher(cursor)

        if teacher_id is None:
            return jsonify({
                "error": "ไม่พบข้อมูลครู"
            }), 403

        room_code = room_code.upper()

        cursor.execute(
            """
            SELECT CLASSROOM_ID
            FROM U.CLASSROOMS
            WHERE ROOM_CODE = :room_code
              AND TEACHER_ID = :teacher_id
            """,
            {
                "room_code": room_code,
                "teacher_id": teacher_id
            }
        )

        room = cursor.fetchone()

        if room is None:
            return jsonify({
                "error": (
                    "ไม่พบห้องเรียนหรือคุณไม่มีสิทธิ์จัดการห้องนี้"
                )
            }), 404

        # อัปเดตสถานะชั่วคราว เพราะ Oracle ยังไม่มีคอลัมน์ STATUS
        settings = get_room_settings(room_code)

        room_settings[room_code] = {
            "duration": settings["duration"],
            "status": status
        }

        return jsonify({
            "message": "เปลี่ยนสถานะห้องเรียนสำเร็จ",
            "room_code": room_code,
            "status": status,
            "notice": "สถานะเก็บไว้ชั่วคราว ไม่ได้บันทึกลง Oracle"
        }), 200

    except Exception:
        return jsonify({
            "error": "ไม่สามารถเปลี่ยนสถานะห้องเรียนได้"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# ==================================================
# 4. ตรวจสอบรหัสห้องเรียน
# GET /api/teacher/rooms/<room_code>/validate
# ==================================================

@teacher_bp.route(
    "/rooms/<room_code>/validate",
    methods=["GET"]
)
def validate_room(room_code):

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT
                CLASSROOM_ID,
                ROOM_NAME,
                ROOM_CODE
            FROM U.CLASSROOMS
            WHERE ROOM_CODE = :room_code
            """,
            {"room_code": room_code.upper()}
        )

        room = cursor.fetchone()

        if room is None:
            return jsonify({
                "valid": False,
                "error": "ไม่พบรหัสห้องเรียน"
            }), 404

        settings = get_room_settings(room[2])

        return jsonify({
            "valid": True,
            "room": {
                "classroom_id": room[0],
                "room_name": room[1],
                "room_code": room[2],
                "duration": settings["duration"],
                "status": settings["status"]
            }
        }), 200

    except Exception:
        return jsonify({
            "error": "ไม่สามารถตรวจสอบรหัสห้องเรียนได้"
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()