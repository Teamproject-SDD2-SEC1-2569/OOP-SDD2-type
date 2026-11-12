import math
import time
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Optional, List


class BaseTypingMode(ABC):
    """
    Abstract Base Class สำหรับโหมดการฝึกพิมพ์
    ประยุกต์ใช้หลัก OOP (Open/Closed Principle & Abstraction)
    """
    def __init__(self, target_text: str):
        self._target_text = target_text
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._total_chars_typed = 0
        self._correct_chars = 0
        self._is_completed = False
        self._is_flagged = False  # ตัวแปรตรวจจับการโกง / บอท (TM-03)
        self._flag_reason = ""
        self._keystroke_timestamps: List[float] = []

    @property
    def target_text(self) -> str:
        return self._target_text

    @property
    def is_started(self) -> bool:
        return self._start_time is not None

    @property
    def is_flagged(self) -> bool:
        return self._is_flagged

    @property
    def flag_reason(self) -> str:
        return self._flag_reason

    def start_session(self):
        if not self.is_started:
            self._start_time = datetime.now()

    def process_keystroke(self, is_correct: bool):
        now_ts = time.time()
        self._keystroke_timestamps.append(now_ts)
        self._total_chars_typed += 1
        if is_correct:
            self._correct_chars += 1

        # Anti-Bot Keystroke Dynamics Analysis (IKI Uniformity)
        if len(self._keystroke_timestamps) >= 15:
            recent_times = self._keystroke_timestamps[-25:]
            intervals = [recent_times[i] - recent_times[i - 1] for i in range(1, len(recent_times))]
            if intervals:
                mean_interval = sum(intervals) / len(intervals)
                variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
                std_dev = math.sqrt(variance)

                # จังหวะพิมพ์สม่ำเสมอเกินไปจนผิดธรรมชาติมนุษย์ (Standard Deviation < 4ms)
                if std_dev < 0.004:
                    self._is_flagged = True
                    self._flag_reason = f"ตรวจพบจังหวะการกดแป้นพิมพ์สม่ำเสมอแบบบอท (std_dev: {round(std_dev * 1000, 2)}ms)"

                # ความเร็วในการเคาะแป้นเฉลี่ยเร็วกว่า 30ms ต่อตัวอักษร
                if mean_interval < 0.030:
                    self._is_flagged = True
                    self._flag_reason = f"ความเร็วในการกดแป้นพิมพ์สูงเกินขีดจำกัดมนุษย์ (avg: {round(mean_interval * 1000, 1)}ms/char)"

    @abstractmethod
    def calculate_score(self) -> int:
        pass

    def get_current_stats(self) -> dict:
        if not self.is_started or self._total_chars_typed == 0:
            return {"wpm": 0, "accuracy": 0.0, "is_flagged": self._is_flagged, "flag_reason": self._flag_reason, "time_spent": 0, "error_count": 0}

        # เวลาที่ใช้ไป (วินาที)
        time_elapsed_sec = (datetime.now() - self._start_time).total_seconds()
        time_elapsed_min = time_elapsed_sec / 60.0
        
        if time_elapsed_min <= 0:
            return {"wpm": 0, "accuracy": 0.0, "is_flagged": self._is_flagged, "flag_reason": self._flag_reason, "time_spent": 0, "error_count": 0}

        gross_wpm = (self._correct_chars / 5.0) / time_elapsed_min
        accuracy = (self._correct_chars / self._total_chars_typed) * 100.0
        
        # คำนวณคำผิด (พิมพ์ทั้งหมด - พิมพ์ถูก)
        error_count = self._total_chars_typed - self._correct_chars

        if time_elapsed_sec > 2.0 and gross_wpm > 240:
            self._is_flagged = True
            self._flag_reason = f"ความเร็วเกินเพดานสูงสุดของมนุษย์ ({round(gross_wpm)} WPM)"

        return {
            "wpm": round(gross_wpm),
            "accuracy": round(accuracy, 2),
            "is_flagged": self._is_flagged,
            "flag_reason": self._flag_reason,
            "time_spent": round(time_elapsed_sec, 2),
            "error_count": error_count
        }


class StandardTypingSession(BaseTypingMode):
    """
    โหมดการฝึกพิมพ์มาตรฐาน คำนวณ WPM, ความแม่นยำ และคะแนนรวม
    """
    def __init__(self, target_text: str):
        super().__init__(target_text)
        
    def calculate_score(self) -> int:
        # หากถูก Flag ว่าโกง ปรับคะแนนเป็น 0 ทันที
        if self._is_flagged:
            return 0
        stats = self.get_current_stats()
        final_score = stats["wpm"] * (stats["accuracy"] / 100) * 10
        return round(final_score)
        
    def finalize_session(self) -> Optional[dict]:
        if self._is_completed:
            return None
            
        self._end_time = datetime.now()
        self._is_completed = True
        
        stats = self.get_current_stats()
        stats["score"] = self.calculate_score()
        return stats
