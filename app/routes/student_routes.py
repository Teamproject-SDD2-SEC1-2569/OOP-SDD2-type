"""
Student Web Views & API Controller
จัดการ Route สำหรับหน้าเว็บฝั่งนักเรียนและเชื่อมต่อฐานข้อมูล Oracle (USERS, STUDENTS, CLASSROOMS, CLASSROOM_MEMBERS, SUBMISSION_RESULTS)
"""
import os
import random
import logging
from dotenv import load_dotenv
from flask import Blueprint, current_app, jsonify, render_template, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from ..database import get_db_connection
from ..services.storage_service import upload_profile_image
from .auth_routes import in_memory_users
from .teacher_routes import active_rooms, room_settings

logger = logging.getLogger(__name__)

student_bp = Blueprint('api', __name__)


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


def _ensure_student_record(cursor, user_id: int) -> None:
    """ตรวจสอบว่ามีข้อมูลใน U.STUDENTS สำหรับ user_id นี้หรือยัง หากยังไม่มีให้สร้างอัตโนมัติ"""
    cursor.execute(
        "SELECT STUDENT_ID FROM U.STUDENTS WHERE STUDENT_ID = :user_id",
        {"user_id": user_id}
    )
    if cursor.fetchone() is None:
        cursor.execute(
            """
            INSERT INTO U.STUDENTS (STUDENT_ID, STUDENT_CODE, MAJOR)
            VALUES (:user_id, :code, :major)
            """,
            {
                "user_id": user_id,
                "code": f"68{user_id:06d}",
                "major": "วิทยาการคอมพิวเตอร์ / IT"
            }
        )


def _resolve_assignment_id(cursor, room_code: str = "") -> int:
    """ค้นหาหรือสร้าง ASSIGNMENT_ID สำหรับห้องเรียน (หรือใช้ Assignment ฝึกซ้อมเริ่มต้น)"""
    if room_code:
        cursor.execute(
            "SELECT CLASSROOM_ID, TEACHER_ID FROM U.CLASSROOMS WHERE UPPER(ROOM_CODE) = UPPER(:code)",
            {"code": room_code.strip()}
        )
        room_row = cursor.fetchone()
        if room_row:
            classroom_id, teacher_id = room_row[0], room_row[1]
            cursor.execute(
                """
                SELECT ASSIGNMENT_ID FROM U.ASSIGNMENTS
                WHERE CLASSROOM_ID = :cid
                ORDER BY ASSIGNMENT_ID DESC
                """,
                {"cid": classroom_id}
            )
            assign_row = cursor.fetchone()
            if assign_row:
                return int(assign_row[0])

            # หากห้องนี้ยังไม่มี Assignment ใน DB ให้ผูกกับ TYPING_TEXTS อัตโนมัติ
            cursor.execute("SELECT TEXT_ID FROM U.TYPING_TEXTS ORDER BY TEXT_ID ASC")
            text_row = cursor.fetchone()
            if text_row:
                text_id = int(text_row[0])
            else:
                text_id_var = cursor.var(int)
                cursor.execute(
                    """
                    INSERT INTO U.TYPING_TEXTS (TITLE, CONTENT, DIFFICULTY, CREATED_BY)
                    VALUES ('Basic Typing Practice', 'apple banana computer desk window school', 'Easy', :created_by)
                    RETURNING TEXT_ID INTO :tid
                    """,
                    {"created_by": teacher_id, "tid": text_id_var}
                )
                tid_val = text_id_var.getvalue()
                text_id = int(tid_val[0] if isinstance(tid_val, list) else tid_val)

            assign_id_var = cursor.var(int)
            cursor.execute(
                """
                INSERT INTO U.ASSIGNMENTS (CLASSROOM_ID, TEXT_ID)
                VALUES (:cid, :tid)
                RETURNING ASSIGNMENT_ID INTO :aid
                """,
                {"cid": classroom_id, "tid": text_id, "aid": assign_id_var}
            )
            aid_val = assign_id_var.getvalue()
            return int(aid_val[0] if isinstance(aid_val, list) else aid_val)

    # กรณีโหมดฝึกซ้อมส่วนตัว ใช้ Assignment แรกที่มีในระบบ
    cursor.execute("SELECT ASSIGNMENT_ID FROM U.ASSIGNMENTS ORDER BY ASSIGNMENT_ID ASC")
    first_assign = cursor.fetchone()
    return int(first_assign[0]) if first_assign else 2


# ==================================================
# Web Page Routes (Frontend Views)
# ==================================================

@student_bp.route('/')
def login():
    """หน้าแรก: เข้าสู่ระบบสำหรับนักเรียนและอาจารย์"""
    load_dotenv(override=True)
    google_client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    current_app.config["GOOGLE_CLIENT_ID"] = google_client_id
    current_app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    return render_template('student/login.html', google_client_id=google_client_id)


@student_bp.route('/register')
def register():
    """หน้าสมัครสมาชิก"""
    return render_template('student/register.html')


@student_bp.route("/join", methods=["GET"])
def join_room_page():
    """หน้ารวม/กรอกรหัสเพื่อเข้าร่วมห้องเรียน"""
    return render_template("student/join.html")


@student_bp.route('/classroom')
def classroom():
    """หน้าห้องเรียนของนักเรียน"""
    return render_template('student/classroom.html')


@student_bp.route('/progress')
def progress():
    """หน้าดูความคืบหน้าและสถิติพัฒนาการ"""
    return render_template('student/progress.html')


@student_bp.route('/typing')
def typing():
    """หน้า Interactive Typing Arena สำหรับฝึกพิมพ์"""
    return render_template('student/typing.html')


@student_bp.route('/classrooms')
def student_classrooms_page():
    """หน้ารวมห้องเรียนของนักเรียน"""
    return render_template('student/classroom.html')


@student_bp.route('/profile')
def student_profile_page():
    """หน้าโปรไฟล์ของนักเรียน"""
    return render_template('student/profile.html')


@student_bp.route('/history')
def typing_history():
    """หน้าประวัติการพิมพ์ที่ผ่านมา"""
    return render_template('student/typing_history.html')


@student_bp.route('/result')
def typing_result():
    """หน้าสรุปผลคะแนนการพิมพ์"""
    return render_template('student/typing-result.html')


# ==================================================
# Student REST APIs (Connected to Oracle Database)
# ==================================================

@student_bp.route('/api/student/profile', methods=['GET'])
@jwt_required()
def get_student_profile():
    """ดึงข้อมูลโปรไฟล์นักเรียนและสถิติการพิมพ์จาก Oracle Database"""
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
            _ensure_student_record(cursor, user_id)
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
                       s.STUDENT_CODE, s.MAJOR{extra_select}
                FROM U.USERS u
                LEFT JOIN U.STUDENTS s ON u.USER_ID = s.STUDENT_ID
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
                """
                SELECT COUNT(*),
                       NVL(ROUND(AVG(WPM), 0), 0),
                       NVL(ROUND(AVG(ACCURACY), 1), 0),
                       NVL(MAX(WPM), 0),
                       NVL(MAX(GRADE_OR_SCORE), 0)
                FROM U.SUBMISSION_RESULTS
                WHERE STUDENT_ID = :user_id
                """,
                {"user_id": user_id}
            )
            stats_row = cursor.fetchone() or (0, 0, 0, 0, 0)

            created_at_str = (
                row[5].strftime("%d/%m/%Y") if row[5] else "-"
            )

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
                    "student_code": row[6] or f"68{row[0]:06d}",
                    "major": row[7] or "General",
                    "profile_image_url": profile_image_url
                },
                "stats": {
                    "total_tests": int(stats_row[0] or 0),
                    "avg_wpm": int(stats_row[1] or 0),
                    "avg_accuracy": float(stats_row[2] or 0),
                    "best_wpm": int(stats_row[3] or 0),
                    "best_score": float(stats_row[4] or 0)
                }
            }), 200
    except Exception as e:
        return jsonify({"error": f"ดึงข้อมูลโปรไฟล์ไม่สำเร็จ: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/profile', methods=['PUT'])
@jwt_required()
def update_student_profile():
    """แก้ไขข้อมูลส่วนตัวของนักเรียนใน U.USERS และ U.STUDENTS"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    data = request.get_json(silent=True) or {}
    if "email" in data:
        # ล็อกไม่ให้แก้ไขฟิลด์ EMAIL ของบัญชีผู้ใช้
        data.pop("email", None)
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    combined_name = f"{first_name} {last_name}".strip()
    full_name = combined_name or (data.get("full_name") or "").strip()
    if not first_name and full_name:
        parts = full_name.split(None, 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""
    student_code = (data.get("student_code") or "").strip()
    major = (data.get("major") or "").strip()

    if not full_name:
        return jsonify({"error": "กรุณาระบุชื่อ-นามสกุล"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            _ensure_student_record(cursor, user_id)

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
            if student_code or major:
                cursor.execute(
                    """
                    UPDATE U.STUDENTS
                    SET STUDENT_CODE = NVL(:code, STUDENT_CODE),
                        MAJOR = NVL(:major, MAJOR)
                    WHERE STUDENT_ID = :user_id
                    """,
                    {
                        "code": student_code if student_code else None,
                        "major": major if major else None,
                        "user_id": user_id
                    }
                )
            conn.commit()
            return jsonify({"message": "อัปเดตข้อมูลโปรไฟล์สำเร็จ"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"อัปเดตข้อมูลไม่สำเร็จ: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/profile', methods=['DELETE'])
@jwt_required()
def delete_student_profile():
    """ลบบัญชีผู้ใช้นักเรียนและข้อมูลที่เกี่ยวข้องออกจากฐานข้อมูล"""
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
            cursor.execute("DELETE FROM U.SUBMISSION_RESULTS WHERE STUDENT_ID = :user_id", {"user_id": user_id})
            cursor.execute("DELETE FROM U.CLASSROOM_MEMBERS WHERE STUDENT_ID = :user_id", {"user_id": user_id})
            cursor.execute("DELETE FROM U.STUDENTS WHERE STUDENT_ID = :user_id", {"user_id": user_id})
            cursor.execute("DELETE FROM U.USERS WHERE USER_ID = :user_id", {"user_id": user_id})
            conn.commit()
            return jsonify({"message": "ลบบัญชีผู้ใช้เรียบร้อยแล้ว"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"ไม่สามารถลบบัญชีผู้ใช้ได้: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/profile/avatar', methods=['POST'])
@jwt_required()
def upload_student_avatar():
    """อัปโหลดรูปโปรไฟล์ของนักเรียน (รองรับ OCI Object Storage พร้อม Fallback บันทึกในเครื่อง)"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    file = request.files.get('avatar') or request.files.get('file')
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

    # อัปเดต In-Memory เผื่อไว้
    if user_id in in_memory_users:
        in_memory_users[user_id]["profile_image_url"] = image_url

    return jsonify({
        "message": "อัปโหลดรูปภาพโปรไฟล์สำเร็จ",
        "profile_image_url": image_url
    }), 200


@student_bp.route('/api/student/profile/avatar', methods=['DELETE'])
@jwt_required()
def delete_student_avatar():
    """ลบรูปโปรไฟล์ของนักเรียน (คืนค่าเป็นค่าเริ่มต้น)"""
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


@student_bp.route('/api/student/classrooms', methods=['GET'])
@jwt_required()
def get_student_classrooms():
    """ดึงรายการห้องเรียนทั้งหมดที่นักเรียนเข้าร่วมจาก U.CLASSROOM_MEMBERS และ U.CLASSROOMS"""
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
            _ensure_student_record(cursor, user_id)
            conn.commit()

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM all_tab_columns
                WHERE owner = 'U'
                  AND table_name = 'CLASSROOMS'
                  AND column_name IN ('STATUS', 'DURATION')
                """
            )
            has_classroom_cols = (cursor.fetchone()[0] or 0) == 2

            if has_classroom_cols:
                cursor.execute(
                    """
                    SELECT c.CLASSROOM_ID, c.ROOM_NAME, c.ROOM_CODE,
                           u.FULL_NAME AS TEACHER_NAME,
                           cm.JOINED_AT,
                           (
                               SELECT NVL(MAX(sr.WPM), 0)
                               FROM U.SUBMISSION_RESULTS sr
                               JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                               WHERE sr.STUDENT_ID = :user_id AND a.CLASSROOM_ID = c.CLASSROOM_ID
                           ) AS BEST_WPM,
                           c.STATUS,
                           c.DURATION
                    FROM U.CLASSROOM_MEMBERS cm
                    JOIN U.CLASSROOMS c ON cm.CLASSROOM_ID = c.CLASSROOM_ID
                    LEFT JOIN U.USERS u ON c.TEACHER_ID = u.USER_ID
                    WHERE cm.STUDENT_ID = :user_id
                    ORDER BY cm.JOINED_AT DESC
                    """,
                    {"user_id": user_id}
                )
            else:
                cursor.execute(
                    """
                    SELECT c.CLASSROOM_ID, c.ROOM_NAME, c.ROOM_CODE,
                           u.FULL_NAME AS TEACHER_NAME,
                           cm.JOINED_AT,
                           (
                               SELECT NVL(MAX(sr.WPM), 0)
                               FROM U.SUBMISSION_RESULTS sr
                               JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                               WHERE sr.STUDENT_ID = :user_id AND a.CLASSROOM_ID = c.CLASSROOM_ID
                           ) AS BEST_WPM
                    FROM U.CLASSROOM_MEMBERS cm
                    JOIN U.CLASSROOMS c ON cm.CLASSROOM_ID = c.CLASSROOM_ID
                    LEFT JOIN U.USERS u ON c.TEACHER_ID = u.USER_ID
                    WHERE cm.STUDENT_ID = :user_id
                    ORDER BY cm.JOINED_AT DESC
                    """,
                    {"user_id": user_id}
                )
            rooms = []
            for row in cursor.fetchall():
                room_code = row[2]
                mem_room = active_rooms.get(room_code, {})
                settings = room_settings.get(room_code, {})
                db_status = row[6] if has_classroom_cols and len(row) > 6 and row[6] else None
                db_duration = row[7] if has_classroom_cols and len(row) > 7 and row[7] is not None else None
                duration = db_duration or mem_room.get("duration") or settings.get("duration") or 60
                status = db_status or settings.get("status") or ("open" if room_code in active_rooms else "open")

                rooms.append({
                    "classroom_id": row[0],
                    "room_name": row[1],
                    "room_code": room_code,
                    "teacher_name": row[3] or "อาจารย์ประจำวิชา",
                    "joined_at": row[4].strftime("%d/%m/%Y") if row[4] else "-",
                    "best_wpm": int(row[5] or 0),
                    "duration": int(duration),
                    "status": status
                })

            return jsonify({"rooms": rooms}), 200
    except Exception as e:
        return jsonify({"error": f"ไม่สามารถดึงข้อมูลห้องเรียนได้: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/classrooms/join', methods=['POST'])
@jwt_required()
def join_student_classroom():
    """เข้าร่วมห้องเรียนด้วยรหัสห้อง (Room Code) และบันทึกลง U.CLASSROOM_MEMBERS"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    data = request.get_json(silent=True) or {}
    room_code = (data.get("room_code") or "").strip().upper()
    if not room_code:
        return jsonify({"error": "กรุณาระบุรหัสห้องเรียน"}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            _ensure_student_record(cursor, user_id)

            cursor.execute(
                """
                SELECT CLASSROOM_ID, ROOM_NAME, ROOM_CODE
                FROM U.CLASSROOMS
                WHERE UPPER(ROOM_CODE) = UPPER(:code)
                """,
                {"code": room_code}
            )
            room = cursor.fetchone()
            if not room:
                return jsonify({"error": f"ไม่พบห้องเรียนรหัส {room_code} ในระบบ"}), 404

            classroom_id = room[0]

            cursor.execute(
                """
                SELECT MEMBER_ID FROM U.CLASSROOM_MEMBERS
                WHERE CLASSROOM_ID = :cid AND STUDENT_ID = :user_id
                """,
                {"cid": classroom_id, "user_id": user_id}
            )
            if cursor.fetchone():
                return jsonify({
                    "message": "คุณอยู่ในห้องเรียนนี้อยู่แล้ว",
                    "room": {"classroom_id": classroom_id, "room_name": room[1], "room_code": room[2]}
                }), 200

            cursor.execute(
                """
                INSERT INTO U.CLASSROOM_MEMBERS (CLASSROOM_ID, STUDENT_ID)
                VALUES (:cid, :user_id)
                """,
                {"cid": classroom_id, "user_id": user_id}
            )
            conn.commit()

            return jsonify({
                "message": f"เข้าร่วมห้องเรียน {room[1]} ({room[2]}) สำเร็จ!",
                "room": {
                    "classroom_id": classroom_id,
                    "room_name": room[1],
                    "room_code": room[2]
                }
            }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"ไม่สามารถเข้าร่วมห้องเรียนได้: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/classrooms/<room_code>/leave', methods=['DELETE'])
@jwt_required()
def leave_student_classroom(room_code):
    """ออกจากห้องเรียน (ลบข้อมูลจาก U.CLASSROOM_MEMBERS)"""
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
                DELETE FROM U.CLASSROOM_MEMBERS
                WHERE STUDENT_ID = :user_id
                  AND CLASSROOM_ID IN (
                      SELECT CLASSROOM_ID FROM U.CLASSROOMS WHERE UPPER(ROOM_CODE) = UPPER(:code)
                  )
                """,
                {"user_id": user_id, "code": room_code.strip()}
            )
            conn.commit()
            return jsonify({"message": "ออกจากห้องเรียนเรียบร้อยแล้ว"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"ไม่สามารถออกจากห้องเรียนได้: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/submissions', methods=['POST'])
@jwt_required()
def submit_typing_result():
    """บันทึกผลคะแนนการพิมพ์ของนักเรียนลงตาราง U.SUBMISSION_RESULTS"""
    identity = get_jwt_identity()
    try:
        user_id = int(identity)
    except (TypeError, ValueError):
        return jsonify({"error": "รหัสผู้ใช้ไม่ถูกต้อง"}), 400

    data = request.get_json(silent=True) or {}
    wpm = max(0, int(float(data.get("wpm") or 0)))
    accuracy = max(0.0, min(100.0, float(data.get("accuracy") or 0)))
    time_spent = max(1, int(float(data.get("time_spent") or 60)))
    error_count = max(0, int(float(data.get("error_count") or 0)))
    room_code = (data.get("room_code") or "").strip().upper()
    score = round(wpm * (accuracy / 100.0) * 10, 0)

    conn = get_db_connection()
    if not conn:
        return jsonify({"error": "ไม่สามารถเชื่อมต่อฐานข้อมูลได้"}), 500

    try:
        with conn.cursor() as cursor:
            _ensure_student_record(cursor, user_id)
            assignment_id = _resolve_assignment_id(cursor, room_code)

            result_id_var = cursor.var(int)
            cursor.execute(
                """
                INSERT INTO U.SUBMISSION_RESULTS (
                    ASSIGNMENT_ID, STUDENT_ID, WPM, ACCURACY,
                    TIME_SPENT, ERROR_COUNT, GRADE_OR_SCORE, SUBMITTED_AT
                )
                VALUES (
                    :aid, :user_id, :wpm, :acc,
                    :time_spent, :err_cnt, :score, CURRENT_TIMESTAMP
                )
                RETURNING RESULT_ID INTO :rid
                """,
                {
                    "aid": assignment_id,
                    "user_id": user_id,
                    "wpm": wpm,
                    "acc": accuracy,
                    "time_spent": time_spent,
                    "err_cnt": error_count,
                    "score": score,
                    "rid": result_id_var
                }
            )
            rid_val = result_id_var.getvalue()
            result_id = int(rid_val[0] if isinstance(rid_val, list) else rid_val)
            conn.commit()

            return jsonify({
                "message": "บันทึกผลคะแนนสำเร็จ",
                "result": {
                    "result_id": result_id,
                    "wpm": wpm,
                    "accuracy": accuracy,
                    "score": int(score),
                    "time_spent": time_spent,
                    "error_count": error_count,
                    "room_code": room_code
                }
            }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"บันทึกผลคะแนนไม่สำเร็จ: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/history', methods=['GET'])
@jwt_required()
def get_student_history():
    """ดึงประวัติการพิมพ์ทั้งหมดของนักเรียนจาก U.SUBMISSION_RESULTS"""
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
                SELECT sr.RESULT_ID, sr.WPM, sr.ACCURACY, sr.TIME_SPENT,
                       NVL(sr.ERROR_COUNT, 0), NVL(sr.GRADE_OR_SCORE, ROUND(sr.WPM * sr.ACCURACY / 10)),
                       sr.SUBMITTED_AT,
                       c.ROOM_NAME, c.ROOM_CODE
                FROM U.SUBMISSION_RESULTS sr
                LEFT JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                LEFT JOIN U.CLASSROOMS c ON a.CLASSROOM_ID = c.CLASSROOM_ID
                WHERE sr.STUDENT_ID = :user_id
                ORDER BY sr.SUBMITTED_AT DESC NULLS LAST, sr.RESULT_ID DESC
                """,
                {"user_id": user_id}
            )

            history = []
            for row in cursor.fetchall():
                submitted_at = row[6]
                date_str = submitted_at.strftime("%d/%m/%Y") if submitted_at else "-"
                time_str = submitted_at.strftime("%H:%M") if submitted_at else "-"
                history.append({
                    "result_id": row[0],
                    "wpm": int(row[1] or 0),
                    "accuracy": float(row[2] or 0),
                    "time_spent": int(row[3] or 0),
                    "error_count": int(row[4] or 0),
                    "score": int(float(row[5] or 0)),
                    "date": date_str,
                    "time": time_str,
                    "room_name": row[7] or "โหมดฝึกซ้อม",
                    "room_code": row[8] or "-"
                })

            return jsonify({"history": history}), 200
    except Exception as e:
        return jsonify({"error": f"ไม่สามารถดึงประวัติการพิมพ์ได้: {e}"}), 500
    finally:
        conn.close()


@student_bp.route('/api/student/leaderboard', methods=['GET'])
def get_student_leaderboard():
    """ดึงอันดับคะแนนสูงสุด (Leaderboard) จาก U.SUBMISSION_RESULTS"""
    room_code = (request.args.get("room_code") or "").strip().upper()

    conn = get_db_connection()
    if not conn:
        return jsonify({"leaderboard": []}), 200

    try:
        with conn.cursor() as cursor:
            if room_code:
                cursor.execute(
                    """
                    SELECT u.USER_ID, u.FULL_NAME, u.USERNAME,
                           MAX(sr.WPM) AS BEST_WPM,
                           MAX(NVL(sr.GRADE_OR_SCORE, ROUND(sr.WPM * sr.ACCURACY / 10))) AS BEST_SCORE
                    FROM U.SUBMISSION_RESULTS sr
                    JOIN U.USERS u ON sr.STUDENT_ID = u.USER_ID
                    JOIN U.ASSIGNMENTS a ON sr.ASSIGNMENT_ID = a.ASSIGNMENT_ID
                    JOIN U.CLASSROOMS c ON a.CLASSROOM_ID = c.CLASSROOM_ID
                    WHERE UPPER(c.ROOM_CODE) = UPPER(:code)
                    GROUP BY u.USER_ID, u.FULL_NAME, u.USERNAME
                    ORDER BY BEST_SCORE DESC, BEST_WPM DESC
                    FETCH FIRST 10 ROWS ONLY
                    """,
                    {"code": room_code}
                )
            else:
                cursor.execute(
                    """
                    SELECT u.USER_ID, u.FULL_NAME, u.USERNAME,
                           MAX(sr.WPM) AS BEST_WPM,
                           MAX(NVL(sr.GRADE_OR_SCORE, ROUND(sr.WPM * sr.ACCURACY / 10))) AS BEST_SCORE
                    FROM U.SUBMISSION_RESULTS sr
                    JOIN U.USERS u ON sr.STUDENT_ID = u.USER_ID
                    GROUP BY u.USER_ID, u.FULL_NAME, u.USERNAME
                    ORDER BY BEST_SCORE DESC, BEST_WPM DESC
                    FETCH FIRST 10 ROWS ONLY
                    """
                )

            leaderboard = []
            for idx, row in enumerate(cursor.fetchall(), start=1):
                leaderboard.append({
                    "rank": idx,
                    "user_id": row[0],
                    "full_name": row[1] or row[2],
                    "username": row[2],
                    "wpm": int(row[3] or 0),
                    "score": int(float(row[4] or 0))
                })

            return jsonify({"leaderboard": leaderboard}), 200
    except Exception as e:
        return jsonify({"leaderboard": [], "error": str(e)}), 200
    finally:
        conn.close()


__all__ = ["student_bp"]
