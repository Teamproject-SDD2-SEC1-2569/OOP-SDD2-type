from datetime import datetime
from abc import ABC, abstractmethod

class BaseTypingMode(ABC):
    def __init__(self, target_text: str):
        self._target_text = target_text
        self._start_time = None
        self._end_time = None
        self._total_chars_typed = 0
        self._correct_chars = 0
        self._is_completed = False
        self._is_flagged = False  # ตัวแปรตรวจจับการโกง (TM-03)

    @property
    def is_started(self):
        return self._start_time is not None

    @property
    def is_flagged(self):
        return self._is_flagged

    def start_session(self):
        if not self.is_started:
            self._start_time = datetime.now()

    def process_keystroke(self, is_correct: bool):
        self._total_chars_typed += 1
        if is_correct:
            self._correct_chars += 1

    @abstractmethod
    def calculate_score(self):
        pass

    def get_current_stats(self) -> dict:
        if not self.is_started or self._total_chars_typed == 0:
            return {"wpm": 0, "accuracy": 0.0, "is_flagged": self._is_flagged}

        time_elapsed = (datetime.now() - self._start_time).total_seconds() / 60.0
        
        if time_elapsed <= 0:
            return {"wpm": 0, "accuracy": 0.0, "is_flagged": self._is_flagged}

        gross_wpm = (self._correct_chars / 5.0) / time_elapsed
        accuracy = (self._correct_chars / self._total_chars_typed) * 100.0

        # Anti-Cheat: ดักจับความเร็วเกิน 320 WPM หลังจากผ่านไปแล้วอย่างน้อย 2 วินาที (ป้องกัน Spike ช่วงแรก)
        if (datetime.now() - self._start_time).total_seconds() > 2.0 and gross_wpm > 320:
            self._is_flagged = True

        return {
            "wpm": round(gross_wpm),
            "accuracy": round(accuracy, 2),
            "is_flagged": self._is_flagged
        }


class StandardTypingSession(BaseTypingMode):
    def __init__(self, target_text: str):
        super().__init__(target_text)
        
    def calculate_score(self):
        # หากถูก Flag ว่าโกง ปรับคะแนนเป็น 0 ทันที
        if self._is_flagged:
            return 0
        stats = self.get_current_stats()
        final_score = stats["wpm"] * (stats["accuracy"] / 100) * 10
        return round(final_score)
        
    def finalize_session(self):
        if self._is_completed:
            return None
            
        self._end_time = datetime.now()
        self._is_completed = True
        
        stats = self.get_current_stats()
        stats["score"] = self.calculate_score()
        return stats