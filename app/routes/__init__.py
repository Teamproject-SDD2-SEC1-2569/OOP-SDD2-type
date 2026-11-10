"""
Routes Package (Presentation / Controller Layer)
รวม Blueprint ทั้งหมดของระบบ: Auth, Teacher, Student
"""
from .auth_routes import auth_bp
from .teacher_routes import teacher_bp
from .student_routes import student_bp

__all__ = [
    "auth_bp",
    "teacher_bp",
    "student_bp"
]
