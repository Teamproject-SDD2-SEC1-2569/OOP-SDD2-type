import random
from flask import Blueprint, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from .models import StandardTypingSession

# สร้าง Blueprint สำหรับ HTTP Routes ปกติ
api_bp = Blueprint('api', __name__)

# Dictionary เก็บ Session การพิมพ์ของนักเรียนที่กำลังออนไลน์
active_sessions = {}

# 1. กลุ่มคำศัพท์ทั่วไป (คละความยาว)
GENERAL_WORDS = [
    "the", "be", "to", "of", "and", "a", "in", "it", "is", "on", "as", "do", "at", "go", "no", "up", "if", "me",
    "that", "have", "this", "from", "they", "will", "what", "time", "just", "like", "know", "take", "year", "good", "some", "could", "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think", "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even", "new", "want", "because", "any", "these", "give", "day", "most", "us",
    "important", "something", "different", "experience", "information", "everything", "understand", "sometimes", "development", "environment", "government", "education", "especially", "completely", "themselves", "possibility", "technology", "comfortable", "interesting"
]

# 2. กลุ่มคำศัพท์เฉพาะทางโปรแกรมมิ่ง
CODING_WORDS = [
    "python", "def", "init", "self", "return", "print", "import", "from", "class", 
    "pass", "try", "except", "True", "False", "None", "elif", "else", "for", "while", 
    "break", "continue", "lambda", "yield", "with", "async", "await", 
    "str", "int", "float", "list", "dict", "set", "tuple", "map", "filter", "len", "range", "open"
]

def register_socket_events(socketio: SocketIO):
    @socketio.on('connect')
    def handle_connect():
        print(f"[WebSocket] Client connected: {request.sid}")
        emit('server_message', {'msg': 'Connected to Typeclass WebSocket Server'})

    @socketio.on('join_classroom')
    def handle_join_classroom(data):
        room = data.get('room_code')
        join_room(room)
        emit('server_message', {'msg': f'A student joined room {room}'}, room=room)

    @socketio.on('start_typing')
    def handle_start_typing(data):
        session_id = request.sid
        
        # ผสมคำศัพท์โดยให้น้ำหนักคำทั่วไปมากกว่า 2 เท่า
        word_pool = (GENERAL_WORDS * 2) + CODING_WORDS
        
        # สุ่ม 500 คำ
        random_words = random.choices(word_pool, k=500)
        target_text = " ".join(random_words)
        
        active_sessions[session_id] = StandardTypingSession(target_text)
        active_sessions[session_id].start_session()
        
        emit('typing_started', {
            'status': 'success', 
            'text_data': target_text
        })

    @socketio.on('keystroke')
    def handle_keystroke(data):
        session_id = request.sid
        
        if session_id not in active_sessions:
            emit('error', {'msg': 'No active typing session found. Please start first.'})
            return

        typing_session = active_sessions[session_id]
        is_correct = data.get('is_correct', False)
        
        typing_session.process_keystroke(is_correct)
        current_stats = typing_session.get_current_stats()
        
        emit('live_stats', current_stats)

    @socketio.on('submit_score')
    def handle_submit_score():
        session_id = request.sid
        
        if session_id not in active_sessions:
            emit('error', {'msg': 'Session not found or already submitted.'})
            return

        typing_session = active_sessions[session_id]
        final_result = typing_session.finalize_session()
        
        if final_result:
            # TODO: นำ final_result ไป INSERT ลง Oracle Database ที่นี่
            emit('score_finalized', final_result)
            del active_sessions[session_id]
        else:
            emit('error', {'msg': 'Session already completed.'})

    @socketio.on('disconnect')
    def handle_disconnect():
        print(f"[WebSocket] Client disconnected: {request.sid}")
        if request.sid in active_sessions:
            del active_sessions[request.sid]