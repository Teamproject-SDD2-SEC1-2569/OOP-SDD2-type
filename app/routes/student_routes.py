"""
Student Web Views & Controller
จัดการ Route สำหรับหน้าเว็บฝั่งนักเรียน
"""
from flask import Blueprint, render_template

student_bp = Blueprint('api', __name__)


@student_bp.route('/')
def login():
    """หน้าแรก: เข้าสู่ระบบสำหรับนักเรียน"""
    return render_template('student/login.html')


@student_bp.route('/register')
def register():
    """หน้าสมัครสมาชิกสำหรับนักเรียน"""
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


__all__ = ["student_bp"]
