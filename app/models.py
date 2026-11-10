"""
Compatibility shim for legacy imports: from app.models import ...
โมเดลทั้งหมดถูกจัดหมวดหมู่ไว้ใน package app.models แล้ว
"""
from .models.typing_session import BaseTypingMode, StandardTypingSession
from .models.domain import User, Student, Teacher, Classroom, SubmissionResult

__all__ = [
    "BaseTypingMode",
    "StandardTypingSession",
    "User",
    "Student",
    "Teacher",
    "Classroom",
    "SubmissionResult"
]