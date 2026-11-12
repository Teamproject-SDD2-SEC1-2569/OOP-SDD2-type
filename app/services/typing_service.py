"""
Typing Service
จัดการ Business Logic ของการฝึกพิมพ์, สถานะ Session, Leaderboard และ Anti-Cheat
"""
import random
from typing import Dict, Any, Optional, Tuple, List
from ..models.typing_session import StandardTypingSession
from ..utils.constants import GENERAL_WORDS, CODING_WORDS, MAX_WPM_THRESHOLD
from ..database import get_db_connection


class TypingService:
    """
    Service Class สำหรับจัดการเซสชันการพิมพ์ดีดและตารางจัดอันดับแบบ Real-time
    """
    def __init__(self):
        # { sid: {"session": StandardTypingSession, "user_id": str, "username": str, "room": str} }
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        # { room_code: { user_id: {"username": str, "wpm": int, "accuracy": float} } }
        self.room_leaderboards: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def register_user_session(self, sid: str, user_id: str, username: str) -> None:
        """ลงทะเบียนเซสชันผู้ใช้เมื่อเชื่อมต่อ WebSocket"""
        self.active_sessions[sid] = {
            "session": None,
            "user_id": user_id,
            "username": username,
            "room": None
        }

    def get_user_session(self, sid: str) -> Optional[Dict[str, Any]]:
        """ดึงข้อมูลเซสชันของผู้ใช้จาก Socket ID"""
        return self.active_sessions.get(sid)

    def join_room(self, sid: str, room_code: str) -> None:
        """บันทึกห้องเรียนที่ผู้ใช้เข้าร่วมและเตรียม Leaderboard ของห้อง"""
        if sid in self.active_sessions:
            self.active_sessions[sid]["room"] = room_code
        if room_code not in self.room_leaderboards:
            self.room_leaderboards[room_code] = {}

    def start_typing_session(self, sid: str) -> Optional[str]:
        """สุ่มชุดคำศัพท์และเริ่มต้นเซสชันการฝึกพิมพ์ใหม่"""
        if sid not in self.active_sessions:
            return None

        word_pool = (GENERAL_WORDS * 2) + CODING_WORDS
        random_words = random.choices(word_pool, k=500)
        target_text = " ".join(random_words)

        typing_session = StandardTypingSession(target_text)
        typing_session.start_session()
        self.active_sessions[sid]["session"] = typing_session
        return target_text

    def process_keystroke(
        self, sid: str, is_correct: bool
    ) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]], Optional[str]]:
        """ประมวลผลการกดแป้นพิมพ์และอัปเดตตารางคะแนนของห้องเรียน"""
        user_meta = self.active_sessions.get(sid)
        if not user_meta or not user_meta.get("session"):
            return None, None, None

        typing_session: StandardTypingSession = user_meta["session"]
        typing_session.process_keystroke(is_correct)
        current_stats = typing_session.get_current_stats()

        room = user_meta.get("room")
        sorted_leaderboard = None
        if room:
            if room not in self.room_leaderboards:
                self.room_leaderboards[room] = {}
            user_id = user_meta["user_id"]
            self.room_leaderboards[room][user_id] = {
                "username": user_meta["username"],
                "wpm": current_stats["wpm"],
                "accuracy": current_stats["accuracy"]
            }
            sorted_leaderboard = sorted(
                self.room_leaderboards[room].values(),
                key=lambda x: x["wpm"],
                reverse=True
            )

        return current_stats, sorted_leaderboard, room

    def submit_score(self, sid: str, data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """ตรวจสอบ Anti-Cheat คำนวณคะแนน และบันทึกลงฐานข้อมูล Oracle (U.SUBMISSION_RESULTS)"""
        time_spent = max(1, int(float(data.get("time_spent") or 60)))
        final_wpm = max(0, int(float(data.get("wpm") or 0)))
        final_accuracy = max(0.0, min(100.0, float(data.get("accuracy") or 0)))
        error_count = max(0, int(float(data.get("error_count") or 0)))

        user_meta = self.active_sessions.get(sid) or {}
        session = user_meta.get("session")

        # 1. Anti-Cheat & Anti-Bot Verification
        bot_flagged = bool(data.get("bot_flagged"))
        bot_reason = str(data.get("bot_reason") or "")

        if session and session.is_flagged:
            bot_flagged = True
            bot_reason = session.flag_reason or "Session flagged as bot pattern"

        if final_wpm > MAX_WPM_THRESHOLD:
            bot_flagged = True
            bot_reason = f"ความเร็วเกินเพดานสูงสุดของมนุษย์ ({final_wpm} WPM)"

        if time_spent < 5 and final_wpm > 100:
            bot_flagged = True
            bot_reason = f"เวลาในการทดสอบสั้นผิดปกติ ({time_spent}s)"

        teacher_comment = None
        if bot_flagged:
            score = 0
            teacher_comment = f"[ANTI_BOT_FLAGGED] {bot_reason}"
        else:
            # คำนวณคะแนนรวมตามปกติ
            score = int(round(final_wpm * (final_accuracy / 100.0) * 10, 0))

        raw_uid = data.get("user_id") or user_meta.get("user_id")
        room_code = (data.get("room_code") or user_meta.get("room") or "").strip().upper()

        student_id = None
        try:
            student_id = int(raw_uid)
        except (TypeError, ValueError):
            student_id = None

        # 2. บันทึกลงตาราง U.SUBMISSION_RESULTS ใน Oracle DB
        conn = get_db_connection()
        if conn and student_id is not None:
            try:
                from ..routes.student_routes import _ensure_student_record, _resolve_assignment_id
                cursor = conn.cursor()
                _ensure_student_record(cursor, student_id)
                assignment_id = _resolve_assignment_id(cursor, room_code)

                sql = """
                    INSERT INTO U.SUBMISSION_RESULTS 
                    (ASSIGNMENT_ID, STUDENT_ID, WPM, ACCURACY, TIME_SPENT, ERROR_COUNT, GRADE_OR_SCORE, TEACHER_COMMENT, SUBMITTED_AT)
                    VALUES (:1, :2, :3, :4, :5, :6, :7, :8, CURRENT_TIMESTAMP)
                """
                cursor.execute(
                    sql,
                    (assignment_id, student_id, final_wpm, final_accuracy, time_spent, error_count, score, teacher_comment)
                )
                conn.commit()
                cursor.close()
                print(f"✅ [DB] Successfully saved score: {score} (Flagged: {bot_flagged}) for student_id: {student_id}")
                return True, {
                    "status": "flagged" if bot_flagged else "success",
                    "message": "ตรวจพบบอท ผลคะแนนถูกระงับ" if bot_flagged else "Score saved successfully!",
                    "score": score,
                    "bot_flagged": bot_flagged,
                    "flag_reason": bot_reason
                }
            except Exception as e:
                print(f"❌ [DB] Error saving score: {e}")
                return False, {
                    "status": "error",
                    "message": f"Database insertion failed: {e}",
                    "score": score
                }
            finally:
                conn.close()
        else:
            if conn:
                conn.close()
            return True, {
                "status": "success",
                "message": "Score calculated (session mode).",
                "score": score
            }

    def remove_session(self, sid: str) -> None:
        """ลบข้อมูลเซสชันเมื่อผู้ใช้ตัดการเชื่อมต่อ"""
        if sid in self.active_sessions:
            room = self.active_sessions[sid].get("room")
            user_id = self.active_sessions[sid].get("user_id")
            if room and room in self.room_leaderboards and user_id in self.room_leaderboards[room]:
                del self.room_leaderboards[room][user_id]
            del self.active_sessions[sid]


typing_service = TypingService()

