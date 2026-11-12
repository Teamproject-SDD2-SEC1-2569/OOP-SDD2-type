import secrets
import logging
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from ..utils.auth_utils import require_role
from ..database import get_db_connection
from ..services.storage_service import upload_profile_image
from .auth_routes import in_memory_users
from .route_guards import view_require_auth

logger = logging.getLogger(__name__)

teacher_bp = Blueprint("teacher", __name__)


def _ensure_profile_image_column(cursor) -> bool:
    """ตรวจสอบและเพิ่มคอลัมน์ PROFILE_IMAGE_URL ในตาราง U.USERS หากยังไม่มี"""
    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM all_tab_columns
            WHERE owner = 'U'
              AND table_name = 'USERS'
              AND column_name = 'PROFILE_IMAGE_URL'
            """
        )
        if (cursor.fetchone()[0] or 0) == 0:
            cursor.execute("ALTER TABLE U.USERS ADD (PROFILE_IMAGE_URL VARCHAR2(500))")
        return True
    except Exception as e:
        logger.warning(f"Note on PROFILE_IMAGE_URL column: {e}")
        return False

# เก็บสถานะและระยะเวลาของห้องไว้ชั่วคราวในหน่วยความจำ
# เนื่องจากตาราง CLASSROOMS ยังไม่มีคอลัมน์ STATUS และ DURATION
# ข้อมูลส่วนนี้จะหายไปเมื่อรีสตาร์ตแอปพลิเคชัน
room_settings = {}
# ตัวแปรจำลอง Database ชั่วคราว (In-Memory) ไว้เก็บข้อมูลห้อง
active_rooms = {}

# ระยะเวลาทดสอบที่อนุญาต (วินาที)
ALLOWED_DURATIONS = (15, 30, 60, 120)
# เกณฑ์ผ่านสำหรับรายงานผลคะแนน
PASS_MIN_WPM = 30
PASS_MIN_ACCURACY = 85.0


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
    """ดึง TEACHER_ID ของครูที่เข้าสู่ระบบอยู่ (สร้างแถวใน U.TEACHERS อัตโนมัติหากบัญชีเป็น Teacher แต่ยังไม่มีข้อมูล)"""
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
    if result:
        return result[0]

    if get_jwt().get("role") == "Teacher":
        _ensure_teacher_record(cursor, user_id)
        cursor.connection.commit()
        return user_id

    return None


def get_room_settings(room_code):
    """ดึงสถานะและระยะเวลาของห้องจากหน่วยความจำ"""
    return room_settings.get(
        room_code,
        {
            "duration": 60,
            "status": "closed"
        }
    )


def _has_classroom_status_duration_cols(cursor) -> bool:
    """ตรวจสอบว่าตาราง U.CLASSROOMS มีคอลัมน์ STATUS และ DURATION แล้วหรือยัง"""
    cursor.execute(
        """
        SELECT COUNT(*)
        FROM all_tab_columns
        WHERE owner = 'U'
          AND table_name = 'CLASSROOMS'
          AND column_name IN ('STATUS', 'DURATION')
        """
    )
    row = cursor.fetchone()
    return bool(row and row[0] == 2)


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

    if type(duration) is not int or duration not in ALLOWED_DURATIONS:
        return jsonify({
            "error": "ระยะเวลาต้องเป็น 15, 30, 60 หรือ 120 วินาที"
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
        has_cols = _has_classroom_status_duration_cols(cursor)

        if has_cols:
            cursor.execute(
                """
                INSERT INTO U.CLASSROOMS
                    (ROOM_NAME, ROOM_CODE, TEACHER_ID, STATUS, DURATION)
                VALUES
                    (:room_name, :room_code, :teacher_id, :status, :duration)
                RETURNING CLASSROOM_ID INTO :classroom_id
                """,
                {
                    "room_name": room_name,
                    "room_code": room_code,
                    "teacher_id": teacher_id,
                    "status": "closed",
                    "duration": duration,
                    "classroom_id": classroom_id_var
                }
            )
        else:
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
            }
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

        has_cols = _has_classroom_status_duration_cols(cursor)
        if has_cols:
            cursor.execute(
                """
                SELECT
                    CLASSROOM_ID,
                    ROOM_NAME,
                    ROOM_CODE,
                    TEACHER_ID,
                    CREATED_AT,
                    STATUS,
                    DURATION
                FROM U.CLASSROOMS
                WHERE TEACHER_ID = :teacher_id
                ORDER BY CLASSROOM_ID DESC
                """,
                {"teacher_id": teacher_id}
            )
        else:
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
            db_status = row[5] if has_cols and len(row) > 5 and row[5] else settings["status"]
            db_duration = int(row[6]) if has_cols and len(row) > 6 and row[6] is not None else settings["duration"]

            rooms.append({
                "classroom_id": row[0],
                "room_name": row[1],
                "room_code": room_code,
                "teacher_id": row[3],
                "created_at": (
                    row[4].isoformat() if row[4] else None
                ),
                "duration": db_duration,
                "status": db_status
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

        if _has_classroom_status_duration_cols(cursor):
            cursor.execute(
                """
                UPDATE U.CLASSROOMS
                SET STATUS = :status
                WHERE ROOM_CODE = :room_code
                  AND TEACHER_ID = :teacher_id
                """,
                {
                    "status": status,
                    "room_code": room_code,
                    "teacher_id": teacher_id
                }
            )
            conn.commit()

        settings = get_room_settings(room_code)

        room_settings[room_code] = {
            "duration": settings["duration"],
            "status": status
        }

        # แจ้งนักศึกษาที่อยู่ในห้องแบบ Real-time ว่าสถานะห้องเปลี่ยนแล้ว
        try:
            from .. import socketio
            # ส่งทั้งแบบระบุ room และแบบ broadcast เพื่อให้ครอบคลุมทุกกรณี
            socketio.emit("room_status_changed", {"room_code": room_code, "status": status}, room=room_code)
            socketio.emit("room_status_changed", {"room_code": room_code, "status": status})

            if status == "closed":
                socketio.emit("room_closed", {
                    "room_code": room_code,
                    "status": "closed",
                    "message": "อาจารย์ได้ปิดห้องทดสอบแล้ว"
                }, room=room_code)
                socketio.emit("room_closed", {
                    "room_code": room_code,
                    "status": "closed",
                    "message": "อาจารย์ได้ปิดห้องทดสอบแล้ว"
                })
        except Exception as e:
            logger.error("Failed to emit room events: %s", e)

        return jsonify({
            "message": "เปลี่ยนสถานะห้องเรียนสำเร็จ",
            "room_code": room_code,
            "status": status
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

        has_cols = _has_classroom_status_duration_cols(cursor)
        if has_cols:
            cursor.execute(
                """
                SELECT
                    CLASSROOM_ID,
                    ROOM_NAME,
                    ROOM_CODE,
                    STATUS,
                    DURATION
                FROM U.CLASSROOMS
                WHERE ROOM_CODE = :room_code
                """,
                {"room_code": room_code.upper()}
            )
        else:
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
        db_status = room[3] if has_cols and len(room) > 3 and room[3] else settings["status"]
        db_duration = int(room[4]) if has_cols and len(room) > 4 and room[4] is not None else settings["duration"]

        return jsonify({
            "valid": True,
            "room": {
                "classroom_id": room[0],
                "room_name": room[1],
                "room_code": room[2],
                "duration": db_duration,
                "status": db_status
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


# ==================================================
# 5. Routes สำหรับแสดงผลหน้าเว็บของอาจารย์ (Frontend Views)
# ==================================================

@teacher_bp.route("/login", methods=["GET"])
def teacher_login_page():
    return redirect(url_for('api.login'))


@teacher_bp.route("/register", methods=["GET"])
def teacher_register_page():
    return redirect(url_for('api.register') + '?role=teacher')


@teacher_bp.route("/dashboard", methods=["GET"])
@view_require_auth('teacher')
def teacher_dashboard_page():
    # ข้อมูลห้องเรียนถูกโหลดผ่าน GET /teacher/api/dashboard (ใช้ JWT ของอาจารย์ที่ล็อกอินอยู่)
    return render_template("teacher/Dashboard.html")


@teacher_bp.route("/create-room", methods=["GET", "POST"])
@view_require_auth('teacher')
def teacher_create_room_page():
    # การสร้างห้องย้ายไปใช้ POST /teacher/rooms (ผูกกับอาจารย์ที่ล็อกอินผ่าน JWT) แล้ว
    return redirect(url_for('teacher.teacher_dashboard_page'))


@teacher_bp.route("/manage-classroom", methods=["GET"])
@view_require_auth('teacher')
def teacher_manage_classroom_page():
    room_code = (request.args.get('room_code') or '').strip().upper()
    if not room_code:
        return redirect(url_for('teacher.teacher_dashboard_page'))

    # รายละเอียดห้องถูกโหลดผ่าน GET /teacher/api/rooms/<room_code>
    return render_template("teacher/Manage-Classroom.html", room_code=room_code)


@teacher_bp.route("/menu", methods=["GET"])
@view_require_auth('teacher')
def teacher_menu_page():
    return redirect(url_for('teacher.teacher_dashboard_page'))


@teacher_bp.route("/students", methods=["GET"])
@view_require_auth('teacher')
def teacher_students_page():
    # ในอนาคตจะดึงข้อมูลรายชื่อนักศึกษาจาก Database ส่งไปแสดงผลที่นี่
    return render_template("teacher/students.html")


@teacher_bp.route("/history", methods=["GET"])
@view_require_auth('teacher')
def teacher_history_page():
    # ในอนาคตจะดึงข้อมูลคะแนนสอบจาก Database ส่งไปแสดงผลที่นี่
    return render_template("teacher/history.html")


@teacher_bp.route("/profile", methods=["GET"])
@view_require_auth('teacher')
def teacher_profile_page():
    return render_template("teacher/profile.html")


def _ensure_teacher_record(cursor, user_id: int):
    """ตรวจสอบว่ามีข้อมูลใน U.TEACHERS สำหรับ user_id นี้หรือยัง ถ้ายังไม่มีให้สร้างอัตโนมัติ"""
    cursor.execute("SELECT TEACHER_ID FROM U.TEACHERS WHERE TEACHER_ID = :user_id", {"user_id": user_id})
    if not cursor.fetchone():
        cursor.execute(
            """
            INSERT INTO U.TEACHERS (TEACHER_ID, ACADEMIC_TITLE, FACULTY)
            VALUES (:user_id, :title, :faculty)
            """,
            {
                "user_id": user_id,
                "title": "อ.",
                "faculty": "สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง"
            }
        )


@teacher_bp.route("/api/profile", methods=["GET"])
@jwt_required()
def get_teacher_profile():
    """ดึงข้อมูลโปรไฟล์อาจารย์และจำนวนห้องเรียนจาก Oracle Database"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            _ensure_teacher_record(cursor, user_id)
            has_profile_img_col = _ensure_profile_image_column(cursor)
            conn.commit()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM all_tab_columns
                WHERE owner = 'U'
                  AND table_name = 'USERS'
                  AND column_name IN ('FIRST_NAME', 'LAST_NAME')
                """
            )
            has_split_name_cols = (cursor.fetchone()[0] or 0) == 2

            extra_cols = []
            if has_split_name_cols:
                extra_cols.extend(["u.FIRST_NAME", "u.LAST_NAME"])
            if has_profile_img_col:
                extra_cols.append("u.PROFILE_IMAGE_URL")

            extra_select = (", " + ", ".join(extra_cols)) if extra_cols else ""

            cursor.execute(
                f"""
                SELECT u.USER_ID, u.USERNAME, u.FULL_NAME, u.EMAIL, u.ROLE, u.CREATED_AT,
                       t.ACADEMIC_TITLE, t.FACULTY{extra_select}
                FROM U.USERS u
                LEFT JOIN U.TEACHERS t ON u.USER_ID = t.TEACHER_ID
                WHERE u.USER_ID = :user_id
                """,
                {"user_id": user_id}
            )
            row = cursor.fetchone()
            if not row:
                return jsonify({"error": "ไม่พบข้อมูลผู้ใช้"}), 404

            full_name_val = (row[2] or "").strip()
            name_parts = full_name_val.split(None, 1) if full_name_val else ["", ""]
            idx = 8
            if has_split_name_cols:
                first_name_val = row[idx] if len(row) > idx and row[idx] else name_parts[0]
                idx += 1
                last_name_val = row[idx] if len(row) > idx and row[idx] else (name_parts[1] if len(name_parts) > 1 else "")
                idx += 1
            else:
                first_name_val = name_parts[0]
                last_name_val = name_parts[1] if len(name_parts) > 1 else ""

            profile_image_url = row[idx] if has_profile_img_col and len(row) > idx and row[idx] else None

            cursor.execute(
                "SELECT COUNT(*) FROM U.CLASSROOMS WHERE TEACHER_ID = :user_id",
                {"user_id": user_id}
            )
            total_rooms = int((cursor.fetchone() or [0])[0] or 0)

            created_at_str = row[5].strftime("%d/%m/%Y") if row[5] else "-"

            return jsonify({
                "profile": {
                    "user_id": row[0],
                    "username": row[1],
                    "first_name": first_name_val,
                    "last_name": last_name_val,
                    "full_name": full_name_val,
                    "email": row[3],
                    "role": row[4],
                    "created_at": created_at_str,
                    "academic_title": row[6] or "อ.",
                    "faculty": row[7] or "สถาบันเทคโนโลยีพระจอมเกล้าเจ้าคุณทหารลาดกระบัง",
                    "profile_image_url": profile_image_url,
                    "total_rooms": total_rooms
                }
            }), 200
    except Exception as e:
        return jsonify({"error": f"ดึงข้อมูลโปรไฟล์อาจารย์ไม่สำเร็จ: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/profile", methods=["PUT"])
@jwt_required()
def update_teacher_profile():
    """แก้ไขข้อมูลส่วนตัวของอาจารย์ใน U.USERS และ U.TEACHERS (ล็อกอีเมลไม่ให้แก้ไข)"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    data = request.get_json(silent=True) or {}
    data.pop("email", None)

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    combined_name = f"{first_name} {last_name}".strip()
    full_name = combined_name or (data.get("full_name") or "").strip()
    if not first_name and full_name:
        parts = full_name.split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    academic_title = (data.get("academic_title") or "อ.").strip()
    faculty = (data.get("faculty") or "").strip()

    if not full_name:
        return jsonify({"error": "กรุณาระบุชื่อ-นามสกุล"}), 400

    if first_name and (len(first_name) < 3 or len(first_name) > 30):
        return jsonify({"error": "ชื่อจริงต้องมีความยาวตั้งแต่ 3 ถึง 30 ตัวอักษร"}), 400

    if last_name and (len(last_name) < 3 or len(last_name) > 30):
        return jsonify({"error": "นามสกุลต้องมีความยาวตั้งแต่ 3 ถึง 30 ตัวอักษร"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            _ensure_teacher_record(cursor, user_id)

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM all_tab_columns
                WHERE owner = 'U'
                  AND table_name = 'USERS'
                  AND column_name IN ('FIRST_NAME', 'LAST_NAME')
                """
            )
            has_split_name_cols = (cursor.fetchone()[0] or 0) == 2

            if has_split_name_cols:
                cursor.execute(
                    """
                    UPDATE U.USERS
                    SET FULL_NAME = :full_name,
                        FIRST_NAME = :first_name,
                        LAST_NAME = :last_name
                    WHERE USER_ID = :user_id
                    """,
                    {
                        "full_name": full_name,
                        "first_name": first_name,
                        "last_name": last_name,
                        "user_id": user_id
                    }
                )
            else:
                cursor.execute(
                    "UPDATE U.USERS SET FULL_NAME = :full_name WHERE USER_ID = :user_id",
                    {"full_name": full_name, "user_id": user_id}
                )

            cursor.execute(
                """
                UPDATE U.TEACHERS
                SET ACADEMIC_TITLE = :academic_title,
                    FACULTY = NVL(:faculty, FACULTY)
                WHERE TEACHER_ID = :user_id
                """,
                {
                    "academic_title": academic_title,
                    "faculty": faculty if faculty else None,
                    "user_id": user_id
                }
            )
            conn.commit()
            return jsonify({"message": "อัปเดตข้อมูลโปรไฟล์อาจารย์สำเร็จ"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"อัปเดตข้อมูลไม่สำเร็จ: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/profile", methods=["DELETE"])
@jwt_required()
def delete_teacher_profile():
    """ลบบัญชีผู้ใช้อาจารย์และข้อมูลที่เกี่ยวข้องออกจากฐานข้อมูล"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM U.SUBMISSION_RESULTS
                WHERE ASSIGNMENT_ID IN (
                    SELECT a.ASSIGNMENT_ID
                    FROM U.ASSIGNMENTS a
                    JOIN U.CLASSROOMS c ON a.CLASSROOM_ID = c.CLASSROOM_ID
                    WHERE c.TEACHER_ID = :user_id
                )
                """,
                {"user_id": user_id}
            )
            cursor.execute(
                """
                DELETE FROM U.ASSIGNMENTS
                WHERE CLASSROOM_ID IN (
                    SELECT CLASSROOM_ID FROM U.CLASSROOMS WHERE TEACHER_ID = :user_id
                )
                """,
                {"user_id": user_id}
            )
            cursor.execute(
                """
                DELETE FROM U.CLASSROOM_MEMBERS
                WHERE CLASSROOM_ID IN (
                    SELECT CLASSROOM_ID FROM U.CLASSROOMS WHERE TEACHER_ID = :user_id
                )
                """,
                {"user_id": user_id}
            )
            cursor.execute("DELETE FROM U.CLASSROOMS WHERE TEACHER_ID = :user_id", {"user_id": user_id})
            cursor.execute("DELETE FROM U.TEACHERS WHERE TEACHER_ID = :user_id", {"user_id": user_id})
            cursor.execute("DELETE FROM U.USERS WHERE USER_ID = :user_id", {"user_id": user_id})
            conn.commit()
            return jsonify({"message": "ลบบัญชีผู้ใช้อาจารย์เรียบร้อยแล้ว"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"ไม่สามารถลบบัญชีผู้ใช้ได้: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/profile/avatar", methods=["POST"])
@jwt_required()
def upload_teacher_avatar():
    """อัปโหลดรูปโปรไฟล์ของอาจารย์ (รองรับ OCI Object Storage พร้อม Fallback บันทึกในเครื่อง)"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    file = request.files.get("avatar") or request.files.get("file")
    if not file:
        return jsonify({"error": "กรุณาเลือกไฟล์รูปภาพที่ต้องการอัปโหลด"}), 400

    ok, result = upload_profile_image(file, user_id)
    if not ok:
        return jsonify({"error": result}), 400

    image_url = result

    # บันทึก URL ลงฐานข้อมูล Oracle
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                _ensure_profile_image_column(cursor)
                cursor.execute(
                    """
                    UPDATE U.USERS
                    SET PROFILE_IMAGE_URL = :url
                    WHERE USER_ID = :user_id
                    """,
                    {"url": image_url, "user_id": user_id}
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error updating avatar in DB: {e}")
            if conn:
                conn.rollback()
        finally:
            conn.close()

    if user_id in in_memory_users:
        in_memory_users[user_id]["profile_image_url"] = image_url

    return jsonify({
        "message": "อัปโหลดรูปภาพโปรไฟล์สำเร็จ",
        "profile_image_url": image_url
    }), 200


@teacher_bp.route("/api/profile/avatar", methods=["DELETE"])
@jwt_required()
def delete_teacher_avatar():
    """ลบรูปโปรไฟล์ของอาจารย์ (คืนค่าเป็นค่าเริ่มต้น)"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cursor:
                _ensure_profile_image_column(cursor)
                cursor.execute(
                    """
                    UPDATE U.USERS
                    SET PROFILE_IMAGE_URL = NULL
                    WHERE USER_ID = :user_id
                    """,
                    {"user_id": user_id}
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Error resetting avatar in DB: {e}")
            if conn:
                conn.rollback()
        finally:
            conn.close()

    if user_id in in_memory_users:
        in_memory_users[user_id]["profile_image_url"] = None

    return jsonify({
        "message": "ลบรูปโปรไฟล์เรียบร้อยแล้ว",
        "profile_image_url": None
    }), 200


# ==================================================
# 6. Teacher Data APIs (Dashboard / Classroom / Students / History)
#    ดึงข้อมูลจริงจาก Oracle Database ตามอาจารย์ที่ล็อกอินอยู่ (JWT)
# ==================================================

def _classroom_status_cols_sql(cursor, alias: str = "c") -> str:
    """คืนค่า SQL สำหรับเลือกคอลัมน์ STATUS, DURATION (หรือ NULL หาก Schema ยังไม่มีคอลัมน์)"""
    if _has_classroom_status_duration_cols(cursor):
        return f"{alias}.STATUS, {alias}.DURATION"
    return "NULL, NULL"


def _fmt_dt(value, fmt: str = "%d/%m/%Y %H:%M"):
    return value.strftime(fmt) if value else None


def _num(value, digits: int = 0):
    if value is None:
        return 0
    return round(float(value), digits) if digits else int(round(float(value)))


def _display_name(full_name, username):
    return (full_name or "").strip() or username or "-"


def _get_owned_room(cursor, room_code: str, teacher_id: int):
    """ดึงข้อมูลห้องเรียนที่อาจารย์คนนี้เป็นเจ้าของ (คืน None หากไม่พบ/ไม่มีสิทธิ์)"""
    status_cols = _classroom_status_cols_sql(cursor)
    cursor.execute(
        f"""
        SELECT c.CLASSROOM_ID, c.ROOM_NAME, c.ROOM_CODE, c.CREATED_AT, {status_cols}
        FROM U.CLASSROOMS c
        WHERE UPPER(c.ROOM_CODE) = UPPER(:room_code)
          AND c.TEACHER_ID = :teacher_id
        """,
        {"room_code": room_code.strip(), "teacher_id": teacher_id}
    )
    row = cursor.fetchone()
    if not row:
        return None
    settings = get_room_settings(row[2])
    return {
        "classroom_id": row[0],
        "room_name": row[1],
        "room_code": row[2],
        "created_at": _fmt_dt(row[3]),
        "status": row[4] or settings["status"],
        "duration": int(row[5]) if row[5] is not None else settings["duration"],
    }


@teacher_bp.route("/api/dashboard", methods=["GET"])
@require_role("Teacher")
def api_teacher_dashboard():
    """ภาพรวมห้องเรียนของอาจารย์: รายการห้อง + สถิติจำนวนสมาชิก/การส่งผล"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            teacher_id = get_current_teacher(cursor)
            if teacher_id is None:
                return jsonify({"error": "ไม่พบข้อมูลอาจารย์สำหรับบัญชีนี้"}), 403

            status_cols = _classroom_status_cols_sql(cursor)
            cursor.execute(
                f"""
                SELECT c.CLASSROOM_ID, c.ROOM_NAME, c.ROOM_CODE, c.CREATED_AT, {status_cols},
                       (SELECT COUNT(*) FROM U.CLASSROOM_MEMBERS m
                         WHERE m.CLASSROOM_ID = c.CLASSROOM_ID) AS MEMBER_COUNT,
                       (SELECT COUNT(*) FROM U.SUBMISSION_RESULTS sr
                          JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                         WHERE a.CLASSROOM_ID = c.CLASSROOM_ID) AS SUBMISSION_COUNT
                FROM U.CLASSROOMS c
                WHERE c.TEACHER_ID = :teacher_id
                ORDER BY c.CLASSROOM_ID DESC
                """,
                {"teacher_id": teacher_id}
            )

            rooms = []
            for row in cursor.fetchall():
                settings = get_room_settings(row[2])
                rooms.append({
                    "classroom_id": row[0],
                    "room_name": row[1],
                    "room_code": row[2],
                    "created_at": _fmt_dt(row[3], "%d/%m/%Y"),
                    "status": row[4] or settings["status"],
                    "duration": int(row[5]) if row[5] is not None else settings["duration"],
                    "member_count": int(row[6] or 0),
                    "submission_count": int(row[7] or 0),
                })

            cursor.execute(
                """
                SELECT COUNT(DISTINCT m.STUDENT_ID)
                FROM U.CLASSROOM_MEMBERS m
                JOIN U.CLASSROOMS c ON m.CLASSROOM_ID = c.CLASSROOM_ID
                WHERE c.TEACHER_ID = :teacher_id
                """,
                {"teacher_id": teacher_id}
            )
            total_students = int((cursor.fetchone() or [0])[0] or 0)

            return jsonify({
                "rooms": rooms,
                "stats": {
                    "total_rooms": len(rooms),
                    "open_rooms": sum(1 for r in rooms if r["status"] == "open"),
                    "total_students": total_students,
                    "total_submissions": sum(r["submission_count"] for r in rooms),
                }
            }), 200
    except Exception as e:
        return jsonify({"error": f"ไม่สามารถดึงข้อมูลภาพรวมได้: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/rooms/<room_code>", methods=["GET"])
@require_role("Teacher")
def api_teacher_room_detail(room_code):
    """รายละเอียดห้องเรียน: ข้อมูลห้อง, รายชื่อสมาชิก และผลคะแนนที่บันทึกแล้ว"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            teacher_id = get_current_teacher(cursor)
            if teacher_id is None:
                return jsonify({"error": "ไม่พบข้อมูลอาจารย์สำหรับบัญชีนี้"}), 403

            room = _get_owned_room(cursor, room_code, teacher_id)
            if not room:
                return jsonify({"error": "ไม่พบห้องเรียนหรือคุณไม่มีสิทธิ์จัดการห้องนี้"}), 404

            cursor.execute(
                """
                SELECT u.USER_ID, u.USERNAME, u.FULL_NAME, s.STUDENT_CODE, s.MAJOR, m.JOINED_AT,
                       NVL(st.ATTEMPTS, 0), st.BEST_WPM, st.BEST_ACC, st.AVG_WPM
                FROM U.CLASSROOM_MEMBERS m
                JOIN U.USERS u ON m.STUDENT_ID = u.USER_ID
                LEFT JOIN U.STUDENTS s ON s.STUDENT_ID = u.USER_ID
                LEFT JOIN (
                    SELECT sr.STUDENT_ID,
                           COUNT(*) AS ATTEMPTS,
                           MAX(sr.WPM) AS BEST_WPM,
                           MAX(sr.ACCURACY) AS BEST_ACC,
                           AVG(sr.WPM) AS AVG_WPM
                    FROM U.SUBMISSION_RESULTS sr
                    JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                    WHERE a.CLASSROOM_ID = :cid
                    GROUP BY sr.STUDENT_ID
                ) st ON st.STUDENT_ID = u.USER_ID
                WHERE m.CLASSROOM_ID = :cid
                ORDER BY st.BEST_WPM DESC NULLS LAST, m.JOINED_AT ASC
                """,
                {"cid": room["classroom_id"]}
            )
            members = [{
                "user_id": r[0],
                "username": r[1],
                "full_name": _display_name(r[2], r[1]),
                "student_code": r[3] or "-",
                "major": r[4] or "-",
                "joined_at": _fmt_dt(r[5]),
                "attempts": int(r[6] or 0),
                "best_wpm": _num(r[7]),
                "best_accuracy": _num(r[8], 2),
                "avg_wpm": _num(r[9]),
            } for r in cursor.fetchall()]

            cursor.execute(
                """
                SELECT sr.RESULT_ID, sr.SUBMITTED_AT, u.USERNAME, u.FULL_NAME, s.STUDENT_CODE,
                       sr.WPM, sr.ACCURACY, sr.TIME_SPENT, sr.ERROR_COUNT, sr.GRADE_OR_SCORE
                FROM U.SUBMISSION_RESULTS sr
                JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                JOIN U.USERS u ON sr.STUDENT_ID = u.USER_ID
                LEFT JOIN U.STUDENTS s ON s.STUDENT_ID = u.USER_ID
                WHERE a.CLASSROOM_ID = :cid
                ORDER BY sr.SUBMITTED_AT DESC
                FETCH FIRST 50 ROWS ONLY
                """,
                {"cid": room["classroom_id"]}
            )
            results = [{
                "result_id": r[0],
                "submitted_at": _fmt_dt(r[1]),
                "full_name": _display_name(r[3], r[2]),
                "student_code": r[4] or "-",
                "wpm": _num(r[5]),
                "accuracy": _num(r[6], 2),
                "time_spent": int(r[7] or 0),
                "error_count": int(r[8] or 0),
                "score": _num(r[9]),
            } for r in cursor.fetchall()]

            return jsonify({"room": room, "members": members, "results": results}), 200
    except Exception as e:
        return jsonify({"error": f"ไม่สามารถดึงข้อมูลห้องเรียนได้: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/rooms/<room_code>", methods=["DELETE"])
@require_role("Teacher")
def api_teacher_delete_room(room_code):
    """ลบห้องเรียนพร้อมสมาชิก งานที่มอบหมาย และผลคะแนนที่เกี่ยวข้อง"""
    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            teacher_id = get_current_teacher(cursor)
            if teacher_id is None:
                return jsonify({"error": "ไม่พบข้อมูลอาจารย์สำหรับบัญชีนี้"}), 403

            room = _get_owned_room(cursor, room_code, teacher_id)
            if not room:
                return jsonify({"error": "ไม่พบห้องเรียนหรือคุณไม่มีสิทธิ์จัดการห้องนี้"}), 404

            cid = {"cid": room["classroom_id"]}
            cursor.execute(
                """
                DELETE FROM U.SUBMISSION_RESULTS
                WHERE ASSIGNMENT_ID IN (SELECT ASSIGNMENT_ID FROM U.ASSIGNMENTS WHERE CLASSROOM_ID = :cid)
                """,
                cid
            )
            cursor.execute("DELETE FROM U.ASSIGNMENTS WHERE CLASSROOM_ID = :cid", cid)
            cursor.execute("DELETE FROM U.CLASSROOM_MEMBERS WHERE CLASSROOM_ID = :cid", cid)
            cursor.execute("DELETE FROM U.CLASSROOMS WHERE CLASSROOM_ID = :cid", cid)
            conn.commit()

            room_settings.pop(room["room_code"], None)
            active_rooms.pop(room["room_code"], None)

            # แจ้งนักศึกษาในห้องว่าห้องเรียนถูกลบ/ปิดแล้ว
            try:
                from .. import socketio
                socketio.emit("room_status_changed", {"room_code": room["room_code"], "status": "closed"}, room=room["room_code"])
                socketio.emit("room_status_changed", {"room_code": room["room_code"], "status": "closed"})
                socketio.emit("room_closed", {
                    "room_code": room["room_code"],
                    "status": "closed",
                    "message": f"อาจารย์ได้ลบห้องเรียน {room['room_name']} แล้ว"
                }, room=room["room_code"])
                socketio.emit("room_closed", {
                    "room_code": room["room_code"],
                    "status": "closed",
                    "message": f"อาจารย์ได้ลบห้องเรียน {room['room_name']} แล้ว"
                })
            except Exception as e:
                logger.error("Failed to emit room deletion events: %s", e)

            return jsonify({"message": f"ลบห้องเรียน {room['room_name']} เรียบร้อยแล้ว"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"ไม่สามารถลบห้องเรียนได้: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/students", methods=["GET"])
@require_role("Teacher")
def api_teacher_students():
    """รายชื่อนักศึกษาในห้องเรียนของอาจารย์ (กรองตาม room_code ได้) พร้อมสรุปข้อมูลห้องเรียน"""
    room_code = (request.args.get("room_code") or "").strip().upper()

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            teacher_id = get_current_teacher(cursor)
            if teacher_id is None:
                return jsonify({"error": "ไม่พบข้อมูลอาจารย์สำหรับบัญชีนี้"}), 403

            # 1. ดึงรายการห้องเรียนทั้งหมดของอาจารย์พร้อมสถิติสรุป
            cursor.execute(
                """
                SELECT c.CLASSROOM_ID, c.ROOM_NAME, c.ROOM_CODE, c.STATUS, c.DURATION, c.CREATED_AT,
                       (SELECT COUNT(*) FROM U.CLASSROOM_MEMBERS m WHERE m.CLASSROOM_ID = c.CLASSROOM_ID) AS student_count,
                       (SELECT COUNT(*) FROM U.SUBMISSION_RESULTS sr 
                        JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID 
                        WHERE a.CLASSROOM_ID = c.CLASSROOM_ID) AS tests_completed,
                       (SELECT ROUND(AVG(sr.WPM), 1) FROM U.SUBMISSION_RESULTS sr 
                        JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID 
                        WHERE a.CLASSROOM_ID = c.CLASSROOM_ID) AS avg_wpm,
                       (SELECT ROUND(AVG(sr.ACCURACY), 1) FROM U.SUBMISSION_RESULTS sr 
                        JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID 
                        WHERE a.CLASSROOM_ID = c.CLASSROOM_ID) AS avg_accuracy
                FROM U.CLASSROOMS c
                WHERE c.TEACHER_ID = :teacher_id
                ORDER BY c.CLASSROOM_ID DESC
                """,
                {"teacher_id": teacher_id}
            )
            rooms = []
            current_room = None
            for r in cursor.fetchall():
                r_code = r[2]
                r_info = {
                    "classroom_id": r[0],
                    "room_name": r[1],
                    "room_code": r_code,
                    "status": r[3] or "open",
                    "duration": int(r[4] or 60),
                    "created_at": _fmt_dt(r[5]),
                    "student_count": int(r[6] or 0),
                    "tests_completed": int(r[7] or 0),
                    "avg_wpm": _num(r[8]),
                    "avg_accuracy": _num(r[9], 1),
                }
                rooms.append(r_info)
                if room_code and room_code != "ALL" and r_code.upper() == room_code:
                    current_room = r_info

            # เงื่อนไขการกรองห้องเรียน
            room_filter = ""
            params_members = {"teacher_id": teacher_id}
            params_users = {"teacher_id": teacher_id}
            params_stats = {"teacher_id": teacher_id}

            if room_code and room_code != "ALL":
                room_filter = " AND UPPER(c.ROOM_CODE) = :room_code"
                params_members["room_code"] = room_code
                params_users["room_code"] = room_code
                params_stats["room_code"] = room_code

            # 2. ดึงห้องเรียนของนักศึกษาแต่ละคน
            cursor.execute(
                f"""
                SELECT m.STUDENT_ID, c.ROOM_NAME, c.ROOM_CODE
                FROM U.CLASSROOM_MEMBERS m
                JOIN U.CLASSROOMS c ON m.CLASSROOM_ID = c.CLASSROOM_ID
                WHERE c.TEACHER_ID = :teacher_id{room_filter}
                ORDER BY c.ROOM_NAME
                """,
                params_members
            )
            rooms_by_student = {}
            for sid, room_name, code in cursor.fetchall():
                rooms_by_student.setdefault(sid, []).append({"room_name": room_name, "room_code": code})

            students = []
            if rooms_by_student:
                cursor.execute(
                    f"""
                    SELECT u.USER_ID, u.USERNAME, u.FULL_NAME, u.EMAIL, s.STUDENT_CODE, s.MAJOR
                    FROM U.USERS u
                    LEFT JOIN U.STUDENTS s ON s.STUDENT_ID = u.USER_ID
                    WHERE u.USER_ID IN (
                        SELECT m.STUDENT_ID
                        FROM U.CLASSROOM_MEMBERS m
                        JOIN U.CLASSROOMS c ON m.CLASSROOM_ID = c.CLASSROOM_ID
                        WHERE c.TEACHER_ID = :teacher_id{room_filter}
                    )
                    ORDER BY s.STUDENT_CODE, u.FULL_NAME
                    """,
                    params_users
                )
                user_rows = cursor.fetchall()

                cursor.execute(
                    f"""
                    SELECT sr.STUDENT_ID, COUNT(*), MAX(sr.WPM), MAX(sr.ACCURACY),
                           AVG(sr.WPM), AVG(sr.ACCURACY), NVL(SUM(sr.TIME_SPENT), 0)
                    FROM U.SUBMISSION_RESULTS sr
                    JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                    JOIN U.CLASSROOMS c ON a.CLASSROOM_ID = c.CLASSROOM_ID
                    WHERE c.TEACHER_ID = :teacher_id{room_filter}
                    GROUP BY sr.STUDENT_ID
                    """,
                    params_stats
                )
                stats = {r[0]: r for r in cursor.fetchall()}

                for u in user_rows:
                    st = stats.get(u[0])
                    s_rooms = rooms_by_student.get(u[0], [])
                    students.append({
                        "user_id": u[0],
                        "username": u[1],
                        "full_name": _display_name(u[2], u[1]),
                        "email": u[3],
                        "student_code": u[4] or "-",
                        "major": u[5] or "-",
                        "rooms": s_rooms,
                        "room_count": len(s_rooms),
                        "tests_completed": int(st[1]) if st else 0,
                        "highest_wpm": _num(st[2]) if st else 0,
                        "highest_accuracy": _num(st[3], 2) if st else 0,
                        "avg_wpm": _num(st[4]) if st else 0,
                        "avg_accuracy": _num(st[5], 2) if st else 0,
                        "total_time_seconds": int(st[6] or 0) if st else 0,
                    })

            return jsonify({
                "rooms": rooms,
                "current_room": current_room,
                "filter_room_code": room_code,
                "students": students,
                "total_students": len(students)
            }), 200
    except Exception as e:
        return jsonify({"error": f"ไม่สามารถดึงข้อมูลนักศึกษาได้: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/students/<int:student_id>", methods=["DELETE"])
@require_role("Teacher")
def api_teacher_remove_student(student_id):
    """นำนักศึกษาออกจากห้องเรียนของอาจารย์ (ระบุ room_code เพื่อเลือกเฉพาะห้อง หรือไม่ระบุเพื่อนำออกจากทุกห้อง)"""
    room_code = (request.args.get("room_code") or "").strip().upper()

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            teacher_id = get_current_teacher(cursor)
            if teacher_id is None:
                return jsonify({"error": "ไม่พบข้อมูลอาจารย์สำหรับบัญชีนี้"}), 403

            sql = """
                DELETE FROM U.CLASSROOM_MEMBERS
                WHERE STUDENT_ID = :student_id
                  AND CLASSROOM_ID IN (
                      SELECT CLASSROOM_ID FROM U.CLASSROOMS
                      WHERE TEACHER_ID = :teacher_id
            """
            params = {"student_id": student_id, "teacher_id": teacher_id}
            if room_code:
                sql += " AND UPPER(ROOM_CODE) = :room_code"
                params["room_code"] = room_code
            sql += ")"

            cursor.execute(sql, params)
            removed = cursor.rowcount
            conn.commit()

            if removed == 0:
                return jsonify({"error": "ไม่พบนักศึกษาคนนี้ในห้องเรียนของคุณ"}), 404
            return jsonify({"message": "นำนักศึกษาออกจากห้องเรียนเรียบร้อยแล้ว", "removed": removed}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"ไม่สามารถนำนักศึกษาออกได้: {e}"}), 500
    finally:
        conn.close()


@teacher_bp.route("/api/history", methods=["GET"])
@require_role("Teacher")
def api_teacher_history():
    """ประวัติผลคะแนนทั้งหมดในห้องเรียนของอาจารย์ (กรองตาม room_code ได้)"""
    room_code = (request.args.get("room_code") or "").strip().upper()

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            teacher_id = get_current_teacher(cursor)
            if teacher_id is None:
                return jsonify({"error": "ไม่พบข้อมูลอาจารย์สำหรับบัญชีนี้"}), 403

            cursor.execute(
                """
                SELECT c.CLASSROOM_ID, c.ROOM_NAME, c.ROOM_CODE, c.STATUS, c.DURATION, c.CREATED_AT,
                       (SELECT COUNT(*) FROM U.CLASSROOM_MEMBERS m WHERE m.CLASSROOM_ID = c.CLASSROOM_ID) AS student_count,
                       (SELECT COUNT(*) FROM U.SUBMISSION_RESULTS sr 
                        JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID 
                        WHERE a.CLASSROOM_ID = c.CLASSROOM_ID) AS total_tests,
                       (SELECT ROUND(AVG(sr.WPM), 1) FROM U.SUBMISSION_RESULTS sr 
                        JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID 
                        WHERE a.CLASSROOM_ID = c.CLASSROOM_ID) AS avg_wpm,
                       (SELECT ROUND(AVG(sr.ACCURACY), 1) FROM U.SUBMISSION_RESULTS sr 
                        JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID 
                        WHERE a.CLASSROOM_ID = c.CLASSROOM_ID) AS avg_accuracy
                FROM U.CLASSROOMS c
                WHERE c.TEACHER_ID = :teacher_id
                ORDER BY c.CLASSROOM_ID DESC
                """,
                {"teacher_id": teacher_id}
            )
            rooms = []
            current_room = None
            for r in cursor.fetchall():
                r_code = r[2]
                r_info = {
                    "classroom_id": r[0],
                    "room_name": r[1],
                    "room_code": r_code,
                    "status": r[3] or "open",
                    "duration": int(r[4] or 60),
                    "created_at": _fmt_dt(r[5]),
                    "student_count": int(r[6] or 0),
                    "total_tests": int(r[7] or 0),
                    "avg_wpm": _num(r[8]),
                    "avg_accuracy": _num(r[9], 1),
                }
                rooms.append(r_info)
                if room_code and room_code != "ALL" and r_code.upper() == room_code:
                    current_room = r_info

            room_filter = ""
            params = {"teacher_id": teacher_id}
            if room_code and room_code != "ALL":
                room_filter = " AND UPPER(c.ROOM_CODE) = :room_code"
                params["room_code"] = room_code

            cursor.execute(
                f"""
                SELECT COUNT(*), AVG(sr.WPM), AVG(sr.ACCURACY)
                FROM U.SUBMISSION_RESULTS sr
                JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                JOIN U.CLASSROOMS c ON a.CLASSROOM_ID = c.CLASSROOM_ID
                WHERE c.TEACHER_ID = :teacher_id{room_filter}
                """,
                params
            )
            agg = cursor.fetchone() or (0, None, None)

            cursor.execute(
                f"""
                SELECT sr.RESULT_ID, sr.SUBMITTED_AT, c.ROOM_CODE, c.ROOM_NAME,
                       u.USERNAME, u.FULL_NAME, s.STUDENT_CODE,
                       sr.WPM, sr.ACCURACY, sr.TIME_SPENT, sr.ERROR_COUNT, sr.GRADE_OR_SCORE
                FROM U.SUBMISSION_RESULTS sr
                JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                JOIN U.CLASSROOMS c ON a.CLASSROOM_ID = c.CLASSROOM_ID
                JOIN U.USERS u ON sr.STUDENT_ID = u.USER_ID
                LEFT JOIN U.STUDENTS s ON s.STUDENT_ID = u.USER_ID
                WHERE c.TEACHER_ID = :teacher_id{room_filter}
                ORDER BY sr.SUBMITTED_AT DESC
                FETCH FIRST 500 ROWS ONLY
                """,
                params
            )
            history = []
            for r in cursor.fetchall():
                wpm = _num(r[7])
                acc = _num(r[8], 2)
                history.append({
                    "result_id": r[0],
                    "submitted_at": _fmt_dt(r[1]),
                    "room_code": r[2],
                    "room_name": r[3],
                    "full_name": _display_name(r[5], r[4]),
                    "student_code": r[6] or "-",
                    "wpm": wpm,
                    "accuracy": acc,
                    "time_spent": int(r[9] or 0),
                    "error_count": int(r[10] or 0),
                    "score": _num(r[11]),
                    "passed": wpm >= PASS_MIN_WPM and acc >= PASS_MIN_ACCURACY,
                })

            return jsonify({
                "rooms": rooms,
                "current_room": current_room,
                "filter_room_code": room_code,
                "history": history,
                "stats": {
                    "total_tests": int(agg[0] or 0),
                    "avg_wpm": _num(agg[1]),
                    "avg_accuracy": _num(agg[2], 1),
                },
                "criteria": {"min_wpm": PASS_MIN_WPM, "min_accuracy": PASS_MIN_ACCURACY},
            }), 200
    except Exception as e:
        return jsonify({"error": f"ไม่สามารถดึงประวัติผลคะแนนได้: {e}"}), 500
    finally:
        conn.close()


__all__ = ["teacher_bp"]
