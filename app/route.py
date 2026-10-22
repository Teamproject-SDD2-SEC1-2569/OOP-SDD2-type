import os
import random
import jwt
from flask import Blueprint, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from .models import StandardTypingSession

api_bp = Blueprint('api', __name__)

# เก็บสถานะการพิมพ์ของผู้ใช้: { sid: {"session": StandardTypingSession, "user_id": str, "username": str, "room": str} }
active_sessions = {}

# เก็บข้อมูล Leaderboard สดของแต่ละห้อง: { room_code: { user_id: {"username": str, "wpm": int, "accuracy": float} } }
room_leaderboards = {}

GENERAL_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "it", "is", "on", "as", "do", "at", "go", "no", "up", "if", "me",
    "that", "have", "this", "from", "they", "will", "what", "time", "just", "like", "know", "take", "year", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "important", "something", "different", "experience", "information", "everything", "understand", "sometimes", "development", "environment", "government", "education", "especially", "completely", "themselves", "possibility", "technology", "comfortable", "interesting"
]

CODING_WORDS = [
    "python", "def", "init", "self", "return", "print", "import", "from", "class", 
    "pass", "try", "except", "True", "False", "None", "elif", "else", "for", "while", 
    "break", "continue", "lambda", "yield", "with", "async", "await", 
    "str", "int", "float", "list", "dict", "set", "tuple", "map", "filter", "len", "range", "open"
]

def register_socket_events(socketio: SocketIO):
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

        active_sessions[request.sid] = {
            "session": None,
            "user_id": user_id,
            "username": username,
            "room": None
        }
        emit('server_message', {'msg': f'Welcome {username}! Connected to server.'})

    @socketio.on('join_classroom')
    def handle_join_classroom(data):
        """2. เข้าร่วมห้องเรียนและตั้งค่ากลุ่ม"""
        room = data.get('room_code')
        if not room:
            emit('error', {'msg': 'Room code is required.'})
            return

        join_room(room)
        active_sessions[request.sid]['room'] = room
        
        if room not in room_leaderboards:
            room_leaderboards[room] = {}

        emit('server_message', {'msg': f"{active_sessions[request.sid]['username']} joined room {room}"}, room=room)

    @socketio.on('start_typing')
    def handle_start_typing(data=None):
        session_id = request.sid
        if session_id not in active_sessions:
            emit('error', {'msg': 'Client session not initialized.'})
            return

        word_pool = (GENERAL_WORDS * 2) + CODING_WORDS
        random_words = random.choices(word_pool, k=500)
        target_text = " ".join(random_words)
        
        typing_session = StandardTypingSession(target_text)
        typing_session.start_session()
        active_sessions[session_id]['session'] = typing_session
        
        emit('typing_started', {
            'status': 'success', 
            'text_data': target_text
        })

    @socketio.on('keystroke')
    def handle_keystroke(data):
        session_id = request.sid
        user_meta = active_sessions.get(session_id)
        
        if not user_meta or not user_meta['session']:
            emit('error', {'msg': 'No active typing session found.'})
            return

        typing_session = user_meta['session']
        is_correct = data.get('is_correct', False)
        
        typing_session.process_keystroke(is_correct)
        current_stats = typing_session.get_current_stats()
        
        # ส่งสถิติส่วนบุคคลกลับให้นักเรียนคนนั้น
        emit('live_stats', current_stats)

        # 2. อัปเดต Leaderboard รวมในห้องเรียนแบบ Real-time
        room = user_meta['room']
        if room:
            user_id = user_meta['user_id']
            room_leaderboards[room][user_id] = {
                "username": user_meta['username'],
                "wpm": current_stats['wpm'],
                "accuracy": current_stats['accuracy']
            }
            # เรียงอันดับคะแนน WPM จากมากไปน้อย
            sorted_leaderboard = sorted(
                room_leaderboards[room].values(), 
                key=lambda x: x['wpm'], 
                reverse=True
            )
            emit('room_leaderboard_update', sorted_leaderboard, room=room)

    @socketio.on('submit_score')
    def handle_submit_score():
        session_id = request.sid
        user_meta = active_sessions.get(session_id)
        
        if not user_meta or not user_meta['session']:
            emit('error', {'msg': 'Session not found or already submitted.'})
            return

        typing_session = user_meta['session']
        final_result = typing_session.finalize_session()
        
        if final_result:
            final_result['user_id'] = user_meta['user_id']
            final_result['username'] = user_meta['username']
            emit('score_finalized', final_result)
            user_meta['session'] = None
        else:
            emit('error', {'msg': 'Session already completed.'})

    @socketio.on('disconnect')
    def handle_disconnect():
        session_id = request.sid
        if session_id in active_sessions:
            room = active_sessions[session_id]['room']
            user_id = active_sessions[session_id]['user_id']
            if room and room in room_leaderboards and user_id in room_leaderboards[room]:
                del room_leaderboards[room][user_id]
            del active_sessions[session_id]