"""
route_guards.py
ระบบรักษาความปลอดภัยเส้นทางหน้าเว็บ (View Route Guards)
ป้องกันการเข้าถึงหน้าเว็บผ่าน URL โดยไม่ได้เข้าสู่ระบบ
ตรวจสอบสิทธิ์ผ่าน JWT ใน Cookie / Header ในระดับ Backend ก่อนส่งหน้า HTML
"""
from functools import wraps
from flask import request, redirect, url_for
from flask_jwt_extended import decode_token


def view_require_auth(allowed_role=None):
    """
    Decorator ป้องกันการเข้าถึงหน้าเว็บ (Frontend View) ผ่าน URL โดยไม่ได้เข้าสู่ระบบ
    ตรวจสอบ JWT Token จาก Cookie ('access_token') หรือ Header Authorization
    ถ้าไม่มี Token หรือ Token ไม่ถูกต้อง/หมดอายุ จะ Redirect ไปหน้า Login ทันที
    ถ้ามี Role ไม่ตรงกับหน้าที่กำหนด จะ Redirect ไปยังหน้าหลักของ Role ตัวเอง
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get("access_token")
            auth_header = request.headers.get("Authorization", "")
            if not token and auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()

            if not token:
                # ไม่มี Token ให้ Redirect ไปหน้า Login ทันที (HTTP 302)
                return redirect(url_for('api.login'))

            try:
                decoded = decode_token(token)
                role = (decoded.get("role") or request.cookies.get("user_role") or "").strip().lower()
                target_role = (allowed_role or "").strip().lower() if allowed_role else None

                # ตรวจสอบว่า Role ตรงกับหน้าที่กำหนดหรือไม่
                if target_role and role and role != target_role:
                    if role == 'teacher':
                        return redirect(url_for('teacher.teacher_dashboard_page'))
                    else:
                        return redirect(url_for('api.student_classrooms_page'))
            except Exception:
                # Token หมดอายุ หรือไม่ถูกต้อง ให้ส่งกลับไปหน้าแรกทันที
                return redirect(url_for('api.login'))

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def view_redirect_if_authenticated():
    """
    สำหรับหน้า Login และ Register:
    ถ้าผู้ใช้ล็อกอินอยู่แล้ว (มี Token ใน Cookie ที่ยังไม่หมดอายุ)
    จะพาดิ่งไปยังหน้า Dashboard ของตนเองทันที
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get("access_token")
            auth_header = request.headers.get("Authorization", "")
            if not token and auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()

            if token:
                try:
                    decoded = decode_token(token)
                    role = (decoded.get("role") or request.cookies.get("user_role") or "").strip().lower()
                    if role == 'teacher':
                        return redirect(url_for('teacher.teacher_dashboard_page'))
                    else:
                        return redirect(url_for('api.student_classrooms_page'))
                except Exception:
                    # Token ใน cookie เสีย/หมดอายุ ให้แสดงหน้า Login ตามปกติ
                    pass

            return fn(*args, **kwargs)
        return wrapper
    return decorator
