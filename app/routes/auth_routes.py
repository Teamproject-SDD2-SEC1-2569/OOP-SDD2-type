import json
import os
import re
import random
import urllib.parse
import urllib.request
from datetime import timedelta
from dotenv import load_dotenv
from flask import Blueprint, current_app, jsonify, redirect, request, url_for
from flask_bcrypt import Bcrypt
from flask_jwt_extended import create_access_token
from ..database import get_db_connection

auth_bp = Blueprint("auth", __name__)
bcrypt = Bcrypt()

# Fallback เก็บข้อมูลผู้ใช้ใน Memory กรณีไม่ได้เชื่อมต่อ Oracle Database
in_memory_users = {}


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "กรุณาส่งข้อมูลในรูปแบบ JSON"}), 400

    username = data.get("username")
    password = data.get("password")
    email = data.get("email")
    role = data.get("role", "Student")
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    combined_name = f"{first_name} {last_name}".strip()
    full_name = combined_name or (data.get("full_name") or "").strip() or username

    if not first_name and isinstance(full_name, str) and full_name.strip():
        name_parts = full_name.strip().split(None, 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

    # ตรวจสอบข้อมูลพื้นฐาน
    if not all(
        isinstance(value, str)
        for value in [username, password, full_name, email, role]
    ):
        return jsonify({"error": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400

    username = username.strip()
    password = password
    full_name = full_name.strip()
    email = re.sub(r"[^\x21-\x7E]", "", email).strip().lower()
    role = role.strip().capitalize()

    if not username or not password or not full_name or not email:
        return jsonify({"error": "ห้ามเว้นช่องข้อมูลว่าง"}), 400

    if first_name and (len(first_name) < 3 or len(first_name) > 30):
        return jsonify({"error": "ชื่อจริงต้องมีความยาวตั้งแต่ 3 ถึง 30 ตัวอักษร"}), 400

    if last_name and (len(last_name) < 3 or len(last_name) > 30):
        return jsonify({"error": "นามสกุลต้องมีความยาวตั้งแต่ 3 ถึง 30 ตัวอักษร"}), 400

    if len(username) < 3 or len(username) > 30:
        return jsonify({"error": "ชื่อผู้ใช้ต้องมีความยาวตั้งแต่ 3 ถึง 30 ตัวอักษร"}), 400

    if len(full_name) > 100 or len(email) > 100:
        return jsonify({"error": "ความยาวข้อมูลเกินกว่าที่กำหนด"}), 400

    if not re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", email):
        return jsonify({"error": "รูปแบบอีเมลไม่ถูกต้อง (กรุณาใช้ตัวอักษรภาษาอังกฤษและตัวเลขเท่านั้น)"}), 400

    if len(password) < 8:
        return jsonify({"error": "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร"}), 400

    if not re.search(r"[A-Za-z\u0E00-\u0E7F]", password):
        return jsonify({"error": "รหัสผ่านต้องมีตัวอักษรอย่างน้อย 1 ตัว"}), 400

    if len(password.encode("utf-8")) > 72:
        return jsonify({"error": "รหัสผ่านยาวเกินกว่าที่ระบบรองรับ"}), 400

    if role not in ("Teacher", "Student"):
        return jsonify({
            "error": "บทบาทต้องเป็น Teacher หรือ Student"
        }), 400

    # ตรวจสอบข้อมูลเพิ่มเติมตามบทบาท
    student_code = None
    major = None
    academic_title = None
    faculty = None

    if role == "Student":
        student_code = data.get("student_code")
        major = data.get("major")

        if not isinstance(student_code, str) or not student_code.strip():
            return jsonify({
                "error": "กรุณากรอกรหัสนักศึกษา 8 หลัก"
            }), 400

        student_code = student_code.strip()

        if not re.fullmatch(r"\d{8}", student_code):
            return jsonify({
                "error": "รหัสนักศึกษาต้องเป็นตัวเลข 8 หลักเท่านั้น"
            }), 400

        if not isinstance(major, str) or not major.strip():
            return jsonify({
                "error": "กรุณาเลือกสาขาวิชา"
            }), 400

        major = major.strip()
        allowed_majors = ("คอมพิวเตอร์เทคโนโลยี", "อิเล็กทรอนิกส์และโทรคมนาคม")
        if major not in allowed_majors:
            return jsonify({
                "error": "สาขาวิชาต้องเป็น คอมพิวเตอร์เทคโนโลยี หรือ อิเล็กทรอนิกส์และโทรคมนาคม เท่านั้น"
            }), 400

    else:
        academic_title = data.get("academic_title")
        faculty = data.get("faculty")

        if academic_title is not None:
            if not isinstance(academic_title, str):
                return jsonify({
                    "error": "คำนำหน้าทางวิชาการไม่ถูกต้อง"
                }), 400

            academic_title = academic_title.strip() or None

        if faculty is not None:
            if not isinstance(faculty, str):
                return jsonify({
                    "error": "ข้อมูลคณะไม่ถูกต้อง"
                }), 400

            faculty = faculty.strip() or None

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    connection = None

    try:
        connection = get_db_connection()
        if connection is None:
            raise RuntimeError("Oracle DB unavailable, using in-memory fallback")

        with connection.cursor() as cursor:
            # ตรวจสอบชื่อผู้ใช้และอีเมลซ้ำ
            cursor.execute("""
                SELECT USER_ID
                FROM U.USERS
                WHERE UPPER(USERNAME) = UPPER(:username)
                   OR LOWER(EMAIL) = LOWER(:email)
            """, username=username, email=email)

            if cursor.fetchone():
                return jsonify({
                    "error": "ชื่อผู้ใช้หรืออีเมลนี้ถูกใช้งานแล้ว"
                }), 409

            if role == "Student" and student_code:
                cursor.execute("""
                    SELECT STUDENT_ID
                    FROM U.STUDENTS
                    WHERE STUDENT_CODE = :student_code
                """, student_code=student_code)
                if cursor.fetchone():
                    return jsonify({
                        "error": "รหัสนักศึกษานี้ถูกใช้งานแล้ว"
                    }), 409

            # ตรวจสอบว่าตาราง U.USERS มีคอลัมน์ FIRST_NAME และ LAST_NAME หรือไม่
            cursor.execute("""
                SELECT COUNT(*)
                FROM all_tab_columns
                WHERE owner = 'U'
                  AND table_name = 'USERS'
                  AND column_name IN ('FIRST_NAME', 'LAST_NAME')
            """)
            has_split_name_cols = (cursor.fetchone()[0] or 0) == 2

            # เพิ่มบัญชีผู้ใช้และรับ USER_ID ที่ Oracle สร้างให้อัตโนมัติ
            user_id_var = cursor.var(int)

            if has_split_name_cols:
                cursor.execute("""
                    INSERT INTO U.USERS (
                        USERNAME,
                        PASSWORD_HASH,
                        FULL_NAME,
                        FIRST_NAME,
                        LAST_NAME,
                        EMAIL,
                        ROLE
                    )
                    VALUES (
                        :username,
                        :password_hash,
                        :full_name,
                        :first_name,
                        :last_name,
                        :email,
                        :role
                    )
                    RETURNING USER_ID INTO :user_id
                """,
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    role=role,
                    user_id=user_id_var
                )
            else:
                cursor.execute("""
                    INSERT INTO U.USERS (
                        USERNAME,
                        PASSWORD_HASH,
                        FULL_NAME,
                        EMAIL,
                        ROLE
                    )
                    VALUES (
                        :username,
                        :password_hash,
                        :full_name,
                        :email,
                        :role
                    )
                    RETURNING USER_ID INTO :user_id
                """,
                    username=username,
                    password_hash=password_hash,
                    full_name=full_name,
                    email=email,
                    role=role,
                    user_id=user_id_var
                )

            user_id = user_id_var.getvalue()[0]

            # เพิ่มข้อมูลในตารางตามบทบาท โดยใช้ USER_ID เดียวกัน
            if role == "Student":
                cursor.execute("""
                    INSERT INTO U.STUDENTS (
                        STUDENT_ID,
                        STUDENT_CODE,
                        MAJOR
                    )
                    VALUES (
                        :student_id,
                        :student_code,
                        :major
                    )
                """,
                    student_id=user_id,
                    student_code=student_code,
                    major=major
                )

            else:
                cursor.execute("""
                    INSERT INTO U.TEACHERS (
                        TEACHER_ID,
                        ACADEMIC_TITLE,
                        FACULTY
                    )
                    VALUES (
                        :teacher_id,
                        :academic_title,
                        :faculty
                    )
                """,
                    teacher_id=user_id,
                    academic_title=academic_title,
                    faculty=faculty
                )

        # บันทึกทั้ง USERS และ STUDENTS/TEACHERS พร้อมกัน
        connection.commit()

        return jsonify({
            "message": "สมัครสมาชิกสำเร็จ",
            "user_id": user_id,
            "username": username,
            "role": role
        }), 201

    except Exception as error:
        if connection is not None:
            try:
                connection.rollback()
            except Exception:
                pass

        print("Register DB fallback:", error)
        # บันทึกลง In-Memory Fallback เพื่อให้ใช้งานแอปต่อได้ทันทีแม้ DB มีปัญหา
        for u in in_memory_users.values():
            if u["username"].lower() == username.lower() or u["email"].lower() == email.lower():
                return jsonify({"error": "ชื่อผู้ใช้หรืออีเมลนี้ถูกใช้งานแล้ว"}), 409

        user_id = len(in_memory_users) + 1
        in_memory_users[username.lower()] = {
            "user_id": user_id,
            "username": username,
            "password_hash": password_hash,
            "full_name": full_name,
            "email": email,
            "role": role
        }
        return jsonify({
            "message": "สมัครสมาชิกสำเร็จ",
            "user_id": user_id,
            "username": username,
            "role": role
        }), 201

    finally:
        if connection is not None:
            connection.close()


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "กรุณาส่งข้อมูลในรูปแบบ JSON"}), 400

    username = data.get("username") or data.get("email")
    password = data.get("password")
    requested_role = data.get("role")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "กรุณากรอก Username และ Password"}), 400

    username = username.strip()

    if not username or not password:
        return jsonify({"error": "กรุณากรอก Username และ Password"}), 400

    user = None
    try:
        conn = get_db_connection()
        if conn is not None:
            with conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT USER_ID, USERNAME, PASSWORD_HASH, FULL_NAME, EMAIL, ROLE
                        FROM U.USERS
                        WHERE UPPER(USERNAME) = UPPER(:username)
                           OR LOWER(EMAIL) = LOWER(:username)
                    """, username=username)

                    user = cursor.fetchone()
    except Exception as e:
        print("Login DB fallback:", e)

    if user is None:
        # ตรวจสอบใน In-Memory Fallback
        for u in in_memory_users.values():
            if u["username"].lower() == username.lower() or u["email"].lower() == username.lower():
                user = (
                    u["user_id"],
                    u["username"],
                    u["password_hash"],
                    u["full_name"],
                    u["email"],
                    u["role"]
                )
                break

    if user is None:
        return jsonify({"error": "Username หรือ Password ไม่ถูกต้อง"}), 401

    user_id, db_username, password_hash, full_name, email, role = user

    if not bcrypt.check_password_hash(password_hash, password):
        return jsonify({"error": "Username หรือ Password ไม่ถูกต้อง"}), 401

    expected_role = (requested_role or "Student").strip().lower()
    if role.strip().lower() != expected_role:
        role_th = "อาจารย์" if role.strip().lower() == "teacher" else "นักเรียน"
        selected_th = "อาจารย์" if expected_role == "teacher" else "นักเรียน"
        return jsonify({
            "error": f"ไม่สามารถเข้าสู่ระบบโหมด{selected_th}ได้ เนื่องจากบัญชีนี้เป็นบัญชี{role_th}"
        }), 403

    access_token = create_access_token(
        identity=str(user_id),
        expires_delta=timedelta(hours=1),
        additional_claims={
            "role": role,
            "username": db_username
        }
    )

    return jsonify({
        "message": "เข้าสู่ระบบสำเร็จ",
        "access_token": access_token,
        "token": access_token,
        "user": {
            "user_id": user_id,
            "username": db_username,
            "full_name": full_name,
            "email": email,
            "role": role
        }
    }), 200


def _verify_google_tokens(id_token: str = "", access_token: str = ""):
    """ตรวจสอบ Token จริงกับ Google OAuth 2.0 API และดึงข้อมูลผู้ใช้ (email, name, sub)"""
    if id_token:
        url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            info = json.loads(resp.read().decode("utf-8"))
            client_id = current_app.config.get("GOOGLE_CLIENT_ID")
            if client_id and info.get("aud") != client_id:
                raise ValueError("Google Client ID mismatch")
            return (
                (info.get("email") or "").strip().lower(),
                (info.get("name") or info.get("given_name") or "").strip(),
                (info.get("sub") or "").strip(),
            )
    if access_token:
        req = urllib.request.Request(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            info = json.loads(resp.read().decode("utf-8"))
            return (
                (info.get("email") or "").strip().lower(),
                (info.get("name") or info.get("given_name") or "").strip(),
                (info.get("sub") or "").strip(),
            )
    return "", "", ""


def _find_google_user(email: str, google_id: str):
    """ค้นหาผู้ใช้ Google ใน U.USERS ว่าเคยสมัครสมาชิกไว้แล้วหรือยัง"""
    user = None
    connection = None
    try:
        connection = get_db_connection()
        if connection is not None:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM all_tab_columns
                    WHERE owner = 'U' AND table_name = 'USERS' AND column_name = 'GOOGLE_ID'
                """)
                has_google_col = cursor.fetchone()[0] > 0

                if has_google_col and google_id:
                    cursor.execute("""
                        SELECT USER_ID, USERNAME, PASSWORD_HASH, FULL_NAME, EMAIL, ROLE
                        FROM U.USERS
                        WHERE GOOGLE_ID = :gid OR LOWER(EMAIL) = LOWER(:email)
                    """, gid=google_id, email=email)
                else:
                    cursor.execute("""
                        SELECT USER_ID, USERNAME, PASSWORD_HASH, FULL_NAME, EMAIL, ROLE
                        FROM U.USERS
                        WHERE LOWER(EMAIL) = LOWER(:email)
                    """, email=email)
                user = cursor.fetchone()

                if user is not None and has_google_col and google_id:
                    cursor.execute("""
                        UPDATE U.USERS
                        SET GOOGLE_ID = :gid, AUTH_PROVIDER = 'GOOGLE'
                        WHERE USER_ID = :user_id AND GOOGLE_ID IS NULL
                    """, gid=google_id, user_id=user[0])
                    connection.commit()
    except Exception as e:
        print("Google Login DB lookup fallback:", e)
    finally:
        if connection is not None:
            connection.close()

    # Fallback ใน Memory กรณีไม่ได้ต่อ DB
    if user is None:
        for u in in_memory_users.values():
            if u["email"].lower() == email.lower():
                user = (u["user_id"], u["username"], u["password_hash"], u["full_name"], u["email"], u["role"])
                break

    return user


@auth_bp.route("/google", methods=["POST"])
def google_login():
    """
    เข้าสู่ระบบด้วยบัญชี Google (OAuth 2.0 / Google Identity Services)
    หากอีเมลนี้ยังไม่เคยสมัครสมาชิกในระบบ จะส่งกลับไปหน้าสมัครสมาชิก (/register) เพื่อกรอกข้อมูลก่อน
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "กรุณาส่งข้อมูลในรูปแบบ JSON"}), 400

    id_token = (data.get("credential") or data.get("id_token") or "").strip()
    google_access_token = (data.get("access_token") or "").strip()
    email = (data.get("email") or "").strip().lower()
    full_name = (data.get("full_name") or data.get("name") or "").strip()
    google_id = (data.get("google_id") or data.get("sub") or "").strip()
    requested_role = (data.get("role") or "Student").strip().capitalize()

    if requested_role not in ("Student", "Teacher"):
        requested_role = "Student"

    # หากส่ง id_token หรือ access_token มาจาก Google OAuth จริง ให้ตรวจสอบกับ Google Server โดยตรง
    if id_token or google_access_token:
        try:
            verified_email, verified_name, verified_sub = _verify_google_tokens(id_token, google_access_token)
            if verified_email:
                email = verified_email
            if verified_name:
                full_name = verified_name
            if verified_sub:
                google_id = verified_sub
        except Exception as err:
            return jsonify({"error": f"การยืนยันตัวตนกับ Google ไม่สำเร็จ: {err}"}), 401

    if not email or "@" not in email:
        return jsonify({"error": "กรุณาระบุอีเมล Google ที่ถูกต้อง"}), 400

    user = _find_google_user(email, google_id)

    # หากยังไม่เคยสมัครสมาชิกในระบบ ให้ส่งไปหน้าสมัครสมาชิกพร้อมข้อมูลเบื้องต้นจาก Google
    if user is None:
        base_username = email.split("@")[0][:40]
        reg_params = urllib.parse.urlencode({
            "email": email,
            "username": base_username,
            "full_name": full_name or base_username,
            "role": requested_role,
        })
        return jsonify({
            "needs_registration": True,
            "message": "บัญชี Google นี้ยังไม่เคยสมัครสมาชิก กรุณากรอกข้อมูลเพื่อสมัครสมาชิกก่อนเข้าใช้งาน",
            "redirect_url": f"{url_for('api.register')}?{reg_params}",
            "google_profile": {
                "email": email,
                "username": base_username,
                "full_name": full_name or base_username,
                "role": requested_role,
            }
        }), 200

    user_id, db_username, _, db_full_name, db_email, role = user

    # ตรวจสอบว่า Role ของบัญชีตรงกับปุ่มที่เลือกหรือไม่
    if role.strip().lower() != requested_role.strip().lower():
        role_th = "อาจารย์" if role.strip().lower() == "teacher" else "นักเรียน"
        selected_th = "อาจารย์" if requested_role.strip().lower() == "teacher" else "นักเรียน"
        return jsonify({
            "error": f"ไม่สามารถเข้าสู่ระบบโหมด{selected_th}ได้ เนื่องจากบัญชี Google นี้ผูกไว้เป็นบัญชี{role_th}"
        }), 403

    access_token = create_access_token(
        identity=str(user_id),
        expires_delta=timedelta(hours=1),
        additional_claims={
            "role": role,
            "username": db_username
        }
    )

    return jsonify({
        "message": "เข้าสู่ระบบด้วย Google สำเร็จ",
        "access_token": access_token,
        "token": access_token,
        "user": {
            "user_id": user_id,
            "username": db_username,
            "full_name": db_full_name,
            "email": db_email,
            "role": role
        }
    }), 200


@auth_bp.route("/google/oauth", methods=["GET"])
def google_oauth_redirect():
    """เริ่มต้น OAuth 2.0 Redirect Flow ไปยังหน้าล็อกอินของ Google"""
    load_dotenv(override=True)
    client_id = (os.getenv("GOOGLE_CLIENT_ID") or current_app.config.get("GOOGLE_CLIENT_ID", "")).strip()
    role = request.args.get("role", "Student")
    if not client_id:
        return jsonify({
            "error": "ยังไม่ได้ตั้งค่า GOOGLE_CLIENT_ID ในไฟล์ .env"
        }), 400

    redirect_uri = url_for("auth.google_oauth_callback", _external=True)
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
        "state": role,
    })
    return redirect(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@auth_bp.route("/google/callback", methods=["GET"])
def google_oauth_callback():
    """รับ Authorization Code จาก Google OAuth 2.0 และแลกเป็น JWT Token เข้าสู่ระบบ"""
    load_dotenv(override=True)
    code = request.args.get("code")
    requested_role = (request.args.get("state") or "Student").strip().capitalize()
    if requested_role not in ("Student", "Teacher"):
        requested_role = "Student"

    if not code:
        return redirect(url_for("api.login"))

    client_id = (os.getenv("GOOGLE_CLIENT_ID") or current_app.config.get("GOOGLE_CLIENT_ID", "")).strip()
    client_secret = (os.getenv("GOOGLE_CLIENT_SECRET") or current_app.config.get("GOOGLE_CLIENT_SECRET", "")).strip()
    redirect_uri = url_for("auth.google_oauth_callback", _external=True)

    try:
        token_data = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://oauth2.googleapis.com/token",
            data=token_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            tokens = json.loads(resp.read().decode("utf-8"))

        email, full_name, google_id = _verify_google_tokens(
            id_token=tokens.get("id_token", ""),
            access_token=tokens.get("access_token", ""),
        )
        user = _find_google_user(email, google_id)
        if user is None:
            base_username = email.split("@")[0][:40]
            reg_params = urllib.parse.urlencode({
                "email": email,
                "username": base_username,
                "full_name": full_name or base_username,
                "role": requested_role,
            })
            reg_url = f"{url_for('api.register')}?{reg_params}"
            return redirect(reg_url)

        user_id, db_username, _, db_full_name, db_email, role = user

        if role.strip().lower() != requested_role.strip().lower():
            role_th = "อาจารย์" if role.strip().lower() == "teacher" else "นักเรียน"
            selected_th = "อาจารย์" if requested_role.strip().lower() == "teacher" else "นักเรียน"
            msg = f"ไม่สามารถเข้าสู่ระบบโหมด{selected_th}ได้ เนื่องจากบัญชี Google นี้ผูกไว้เป็นบัญชี{role_th}"
            return f"<script>alert({json.dumps(msg)}); window.location.href='/';</script>"

        jwt_token = create_access_token(
            identity=str(user_id),
            expires_delta=timedelta(hours=1),
            additional_claims={"role": role, "username": db_username},
        )
        user_obj = {
            "user_id": user_id,
            "username": db_username,
            "full_name": db_full_name,
            "email": db_email,
            "role": role,
        }
        target_url = url_for("teacher.teacher_dashboard_page") if role == "Teacher" else url_for("api.classroom")
        return f"""<!DOCTYPE html><html><body><script>
            localStorage.setItem("token", {json.dumps(jwt_token)});
            localStorage.setItem("accessToken", {json.dumps(jwt_token)});
            localStorage.setItem("user", JSON.stringify({json.dumps(user_obj)}));
            localStorage.setItem("username", {json.dumps(db_username)});
            window.location.replace({json.dumps(target_url)});
        </script></body></html>"""
    except Exception as err:
        return f"<script>alert('เข้าสู่ระบบด้วย Google ไม่สำเร็จ: {err}'); window.location.href='/';</script>"
