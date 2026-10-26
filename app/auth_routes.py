import re
from flask import Blueprint, request, jsonify
from flask_bcrypt import Bcrypt
from .database import get_db_connection

auth_bp = Blueprint("auth", __name__)
bcrypt = Bcrypt()


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "กรุณาส่งข้อมูลในรูปแบบ JSON"}), 400

    username = data.get("username")
    password = data.get("password")
    full_name = data.get("full_name")
    email = data.get("email")
    role = data.get("role")

    # ตรวจสอบข้อมูลพื้นฐาน
    if not all(
        isinstance(value, str)
        for value in [username, password, full_name, email, role]
    ):
        return jsonify({"error": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400

    username = username.strip()
    password = password
    full_name = full_name.strip()
    email = email.strip().lower()
    role = role.strip().capitalize()

    if not username or not password or not full_name or not email:
        return jsonify({"error": "ห้ามเว้นช่องข้อมูลว่าง"}), 400

    if len(username) > 50 or len(full_name) > 100 or len(email) > 100:
        return jsonify({"error": "ความยาวข้อมูลเกินกว่าที่กำหนด"}), 400

    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"error": "รูปแบบอีเมลไม่ถูกต้อง"}), 400

    if len(password) < 8:
        return jsonify({"error": "รหัสผ่านต้องมีอย่างน้อย 8 ตัวอักษร"}), 400

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
                "error": "กรุณากรอกรหัสนักศึกษา"
            }), 400

        student_code = student_code.strip()

        if len(student_code) > 20:
            return jsonify({
                "error": "รหัสนักศึกษาต้องไม่เกิน 20 ตัวอักษร"
            }), 400

        if major is not None:
            if not isinstance(major, str):
                return jsonify({
                    "error": "ข้อมูลสาขาวิชาไม่ถูกต้อง"
                }), 400

            major = major.strip() or None

            if major and len(major) > 100:
                return jsonify({
                    "error": "สาขาวิชาต้องไม่เกิน 100 ตัวอักษร"
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

            # เพิ่มบัญชีผู้ใช้และรับ USER_ID ที่ Oracle สร้างให้อัตโนมัติ
            user_id_var = cursor.var(int)

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
            connection.rollback()

        # แสดงรายละเอียดใน Terminal สำหรับช่วยตรวจสอบตอนพัฒนา
        print("Register error:", error)

        return jsonify({
            "error": "ไม่สามารถสมัครสมาชิกได้ กรุณาตรวจสอบข้อมูลและฐานข้อมูล"
        }), 500

    finally:
        if connection is not None:
            connection.close()
    
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "กรุณาส่งข้อมูลในรูปแบบ JSON"}), 400

    username = data.get("username")
    password = data.get("password")

    if not isinstance(username, str) or not isinstance(password, str):
        return jsonify({"error": "กรุณากรอก Username และ Password"}), 400

    username = username.strip()

    if not username or not password:
        return jsonify({"error": "กรุณากรอก Username และ Password"}), 400

    try:
        with get_db_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT USER_ID, USERNAME, PASSWORD_HASH, FULL_NAME, EMAIL, ROLE
                    FROM U.USERS
                    WHERE UPPER(USERNAME) = UPPER(:username)
                """, username=username)

                user = cursor.fetchone()

        if user is None:
            return jsonify({"error": "Username หรือ Password ไม่ถูกต้อง"}), 401

        user_id, db_username, password_hash, full_name, email, role = user

        if not bcrypt.check_password_hash(password_hash, password):
            return jsonify({"error": "Username หรือ Password ไม่ถูกต้อง"}), 401

        from flask_jwt_extended import create_access_token
        from datetime import timedelta

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
            "user": {
                "user_id": user_id,
                "username": db_username,
                "full_name": full_name,
                "email": email,
                "role": role
            }
        }), 200

    except Exception:
        return jsonify({
            "error": "ไม่สามารถเข้าสู่ระบบได้ กรุณาตรวจสอบการเชื่อมต่อฐานข้อมูล"
        }), 500