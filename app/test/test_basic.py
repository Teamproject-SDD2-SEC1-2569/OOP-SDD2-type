from app.models import (
    StandardTypingSession,
    User,
    Student,
    Teacher,
    Classroom,
    SubmissionResult
)
from app.services.typing_service import TypingService


def test_standard_typing_session_flow():
    """ทดสอบการคำนวณสถิติและคะแนนของ StandardTypingSession"""
    target = "python flask typing system"
    session = StandardTypingSession(target)
    
    assert not session.is_started
    assert not session.is_flagged

    session.start_session()
    assert session.is_started

    # จำลองการกดแป้นพิมพ์
    for char in "python":
        session.process_keystroke(is_correct=True)

    stats = session.get_current_stats()
    assert stats["wpm"] >= 0
    assert stats["accuracy"] == 100.0

    final_stats = session.finalize_session()
    assert final_stats is not None
    assert "score" in final_stats


def test_anti_cheat_detection():
    """ทดสอบระบบ Anti-Cheat เมื่อผู้ใช้ทำความเร็ว WPM เกินเกณฑ์ (320 WPM)"""
    service = TypingService()
    sid = "test_socket_sid_999"
    service.register_user_session(sid, "user_1", "TestStudent")

    # ส่งคะแนนที่มี WPM เกินเกณฑ์ 320 WPM
    cheat_payload = {
        "wpm": 350,
        "accuracy": 99.5,
        "time_spent": 10,
        "error_count": 1
    }
    success, res = service.submit_score(sid, cheat_payload)
    assert not success
    assert "Anti-Cheat" in res["message"]


def test_domain_models():
    """ทดสอบ OOP Domain Entities (User, Student, Teacher, Classroom, SubmissionResult)"""
    student = Student(
        user_id=1,
        username="somchai",
        email="somchai@test.com",
        student_code="6501001",
        major="Computer Science",
        full_name="Somchai Dee"
    )
    assert student.is_student()
    assert not student.is_teacher()
    assert student.student_code == "6501001"
    student_dict = student.to_dict()
    assert student_dict["role"] == "Student"

    teacher = Teacher(
        user_id=2,
        username="prof_surachai",
        email="surachai@univ.ac.th",
        academic_title="Asst. Prof.",
        faculty="Information Technology"
    )
    assert teacher.is_teacher()
    assert not teacher.is_student()
    assert teacher.academic_title == "Asst. Prof."

    room = Classroom(
        room_id=10,
        room_code="TYP-1234",
        room_name="Lab Typing 101",
        teacher_id=2
    )
    assert room.is_active
    assert room.room_code == "TYP-1234"

    sub = SubmissionResult(
        assignment_id=2,
        student_id=1,
        accuracy=98.5,
        time_spent=60.0,
        error_count=2,
        score=95.0
    )
    assert sub.accuracy == 98.5
    assert sub.score == 95.0