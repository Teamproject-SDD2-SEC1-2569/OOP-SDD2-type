from datetime import datetime
from typing import Optional, Dict, Any


class User:
    """
    คลาสแม่แทนข้อมูลผู้ใช้งานในระบบ (Base User Entity)
    """
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        role: str,
        full_name: str = "",
        created_at: Optional[datetime] = None
    ):
        self._user_id = user_id
        self._username = username
        self._email = email
        self._role = role
        self._full_name = full_name
        self._created_at = created_at or datetime.now()

    @property
    def user_id(self) -> int:
        return self._user_id

    @property
    def username(self) -> str:
        return self._username

    @property
    def email(self) -> str:
        return self._email

    @property
    def role(self) -> str:
        return self._role

    @property
    def full_name(self) -> str:
        return self._full_name

    def is_teacher(self) -> bool:
        return self._role.lower() == "teacher"

    def is_student(self) -> bool:
        return self._role.lower() == "student"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "email": self._email,
            "role": self._role,
            "full_name": self._full_name,
            "created_at": self._created_at.isoformat() if self._created_at else None
        }


class Student(User):
    """
    คลาสแทนนักเรียน (สืบทอดจาก User) พร้อมข้อมูลรหัสนักศึกษาและสาขาวิชา
    """
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        student_code: str = "",
        major: str = "",
        full_name: str = "",
        created_at: Optional[datetime] = None
    ):
        super().__init__(
            user_id=user_id,
            username=username,
            email=email,
            role="Student",
            full_name=full_name,
            created_at=created_at
        )
        self._student_code = student_code
        self._major = major

    @property
    def student_code(self) -> str:
        return self._student_code

    @property
    def major(self) -> str:
        return self._major

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "student_code": self._student_code,
            "major": self._major
        })
        return data


class Teacher(User):
    """
    คลาสแทนอาจารย์ผู้สอน (สืบทอดจาก User) พร้อมข้อมูลตำแหน่งทางวิชาการและคณะ
    """
    def __init__(
        self,
        user_id: int,
        username: str,
        email: str,
        academic_title: str = "",
        faculty: str = "",
        full_name: str = "",
        created_at: Optional[datetime] = None
    ):
        super().__init__(
            user_id=user_id,
            username=username,
            email=email,
            role="Teacher",
            full_name=full_name,
            created_at=created_at
        )
        self._academic_title = academic_title
        self._faculty = faculty

    @property
    def academic_title(self) -> str:
        return self._academic_title

    @property
    def faculty(self) -> str:
        return self._faculty

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "academic_title": self._academic_title,
            "faculty": self._faculty
        })
        return data


class Classroom:
    """
    คลาสแทนห้องเรียนสำหรับจัดการแข่งขันหรือฝึกพิมพ์
    """
    def __init__(
        self,
        room_id: int,
        room_code: str,
        room_name: str,
        teacher_id: int,
        is_active: bool = True,
        created_at: Optional[datetime] = None
    ):
        self._room_id = room_id
        self._room_code = room_code
        self._room_name = room_name
        self._teacher_id = teacher_id
        self._is_active = is_active
        self._created_at = created_at or datetime.now()

    @property
    def room_id(self) -> int:
        return self._room_id

    @property
    def room_code(self) -> str:
        return self._room_code

    @property
    def room_name(self) -> str:
        return self._room_name

    @property
    def teacher_id(self) -> int:
        return self._teacher_id

    @property
    def is_active(self) -> bool:
        return self._is_active

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self._room_id,
            "room_code": self._room_code,
            "room_name": self._room_name,
            "teacher_id": self._teacher_id,
            "is_active": self._is_active,
            "created_at": self._created_at.isoformat() if self._created_at else None
        }


class SubmissionResult:
    """
    คลาสแทนผลการส่งคะแนนการพิมพ์ (ตรงกับตาราง Submission_Results ใน Oracle)
    """
    def __init__(
        self,
        assignment_id: int,
        student_id: int,
        accuracy: float,
        time_spent: float,
        error_count: int,
        score: float,
        submitted_at: Optional[datetime] = None,
        result_id: Optional[int] = None
    ):
        self._result_id = result_id
        self._assignment_id = assignment_id
        self._student_id = student_id
        self._accuracy = accuracy
        self._time_spent = time_spent
        self._error_count = error_count
        self._score = score
        self._submitted_at = submitted_at or datetime.now()

    @property
    def result_id(self) -> Optional[int]:
        return self._result_id

    @property
    def assignment_id(self) -> int:
        return self._assignment_id

    @property
    def student_id(self) -> int:
        return self._student_id

    @property
    def accuracy(self) -> float:
        return self._accuracy

    @property
    def time_spent(self) -> float:
        return self._time_spent

    @property
    def error_count(self) -> int:
        return self._error_count

    @property
    def score(self) -> float:
        return self._score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self._result_id,
            "assignment_id": self._assignment_id,
            "student_id": self._student_id,
            "accuracy": self._accuracy,
            "time_spent": self._time_spent,
            "error_count": self._error_count,
            "score": self._score,
            "submitted_at": self._submitted_at.isoformat() if self._submitted_at else None
        }
