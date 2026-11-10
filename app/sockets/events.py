"""
SocketIO Event Handlers
แยกการจัดการ Event ทางฝั่ง WebSocket ออกจาก HTTP Route
"""
import os
import jwt
from flask import request
from flask_socketio import SocketIO, emit, join_room
from ..services.typing_service import typing_service


def register_socket_events(socketio: SocketIO):
    """
    ลงทะเบียน WebSocket Event ทั้งหมดสำหรับระบบ Real-time Typing & Leaderboard
    """

    @socketio.on('connect')
    def handle_connect(auth):
        """1. ตรวจสอบ JWT Token ตอนเชื่อมต่อ (TM-02)"""
        token = None
        if auth and isinstance(auth, dict):
            token = auth.get('token')

        secret_key = os.getenv('SECRET_KEY', 'typeclass-super-secret-key')

        try:
            if token:
                payload = jwt.decode(token, secret_key, algorithms=["HS256"])
                user_id = payload.get("user_id")
                username = payload.get("username", "Anonymous")
            else:
                # โหมดทดสอบชั่วคราวหากยังไม่มี token จาก frontend
                user_id = f"guest_{request.sid[:5]}"
                username = f"Student_{request.sid[:4]}"
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            emit('error', {'msg': 'Unauthorized: Invalid or expired token.'})
            return False

        typing_service.register_user_session(request.sid, str(user_id), username)
        emit('server_message', {'msg': f'Welcome {username}! Connected to server.'})

    @socketio.on('join_classroom')
    def handle_join_classroom(data):
        """2. เข้าร่วมห้องเรียนและตั้งค่ากลุ่ม"""
        room = data.get('room_code')
        if not room:
            emit('error', {'msg': 'Room code is required.'})
            return

        join_room(room)
        typing_service.join_room(request.sid, room)

        user_session = typing_service.get_user_session(request.sid)
        username = user_session['username'] if user_session else "Student"
        emit('server_message', {'msg': f"{username} joined room {room}"}, room=room)

    @socketio.on('start_typing')
    def handle_start_typing(data=None):
        """3. เริ่มต้นการพิมพ์ และรับข้อความแบบสุ่ม"""
        target_text = typing_service.start_typing_session(request.sid)
        if not target_text:
            emit('error', {'msg': 'Client session not initialized.'})
            return

        emit('typing_started', {
            'status': 'success',
            'text_data': target_text
        })

    @socketio.on('keystroke')
    def handle_keystroke(data):
        """4. รับสถิติการกดแป้นพิมพ์และกระจายอัปเดต Leaderboard สด"""
        is_correct = data.get('is_correct', False)
        current_stats, sorted_leaderboard, room = typing_service.process_keystroke(
            request.sid, is_correct
        )

        if current_stats is None:
            emit('error', {'msg': 'No active typing session found.'})
            return

        # ส่งสถิติส่วนบุคคลกลับให้นักเรียนคนนั้น
        emit('live_stats', current_stats)

        # อัปเดต Leaderboard รวมในห้องเรียนแบบ Real-time
        if room and sorted_leaderboard is not None:
            emit('room_leaderboard_update', sorted_leaderboard, room=room)

    @socketio.on('submit_score')
    def handle_submit_score(data):
        """5. รับผลคะแนนเมื่อพิมพ์เสร็จ แล้วบันทึกลงฐานข้อมูล Oracle"""
        success, response_payload = typing_service.submit_score(request.sid, data)
        emit('submission_response', response_payload)

    @socketio.on('disconnect')
    def handle_disconnect():
        """6. ตัดการเชื่อมต่อและเคลียร์ข้อมูลในหน่วยความจำ"""
        typing_service.remove_session(request.sid)
