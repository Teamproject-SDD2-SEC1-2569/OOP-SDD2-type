from datetime import datetime
from abc import ABC, abstractmethod

class BaseTypingMode(ABC):
    """
    คลาสต้นแบบ (Abstract Base Class) สำหรับโหมดการพิมพ์
    ใช้หลักการ Polymorphism และ Abstraction เพื่อให้สามารถขยายโหมดการเล่นได้ในอนาคต 
    (เช่น โหมดจับเวลา 1 นาที, โหมดพิมพ์ตามจำนวนคำ)
    """
    def __init__(self, target_text: str):
        # ใช้ Encapsulation (Private Attributes นำหน้าด้วย _) 
        # เพื่อป้องกันการใช้บอท หรือ Client แอบแก้ไขตัวเลขเหล่านี้โดยตรง
        self._target_text = target_text
        self._start_time = None
        self._end_time = None
        self._total_chars_typed = 0
        self._correct_chars = 0
        self._is_completed = False

    @property
    def is_started(self):
        """Property สำหรับเช็กว่าเริ่มพิมพ์หรือยัง"""
        return self._start_time is not None

    def start_session(self):
        """เริ่มจับเวลาเมื่อได้รับสัญญาณจาก WebSocket ว่ากดแป้นแรก"""
        if not self.is_started:
            self._start_time = datetime.now()

    def process_keystroke(self, is_correct: bool):
        """
        ประมวลผลเมื่อมีการกดแป้นพิมพ์ 1 ครั้ง
        ข้อมูลจะถูกอัปเดตผ่าน Method นี้เท่านั้น ไม่สามารถแก้ค่า _correct_chars ตรงๆ ได้
        """
        self._total_chars_typed += 1
        if is_correct:
            self._correct_chars += 1

    @abstractmethod
    def calculate_score(self):
        """Method ที่บังคับให้คลาสลูกต้องนำไปเขียน logic การให้คะแนนของตัวเอง"""
        pass

    def get_current_stats(self) -> dict:
        """คำนวณ WPM และ Accuracy แบบ Real-time (Server-Side Calculation)"""
        if not self.is_started or self._total_chars_typed == 0:
            return {"wpm": 0, "accuracy": 0.0}

        # คำนวณเวลาที่ใช้ไป (นาที)
        time_elapsed = (datetime.now() - self._start_time).total_seconds() / 60.0
        
        # ป้องกันการหารด้วยศูนย์
        if time_elapsed <= 0:
            return {"wpm": 0, "accuracy": 0.0}

        # สูตรคำนวณ WPM มาตรฐาน: (จำนวนตัวอักษรที่พิมพ์ถูก / 5) / เวลาเป็นนาที
        gross_wpm = (self._correct_chars / 5.0) / time_elapsed
        
        # สูตรคำนวณ Accuracy: (พิมพ์ถูก / พิมพ์ทั้งหมด) * 100
        accuracy = (self._correct_chars / self._total_chars_typed) * 100.0

        return {
            "wpm": round(gross_wpm),
            "accuracy": round(accuracy, 2)
        }


class StandardTypingSession(BaseTypingMode):
    """
    คลาสสำหรับโหมดการฝึกพิมพ์ปกติ สืบทอด (Inheritance) มาจาก BaseTypingMode
    """
    def __init__(self, target_text: str):
        super().__init__(target_text)
        
    def calculate_score(self):
        """
        คำนวณคะแนนรวม (Score) ของโหมดนี้
        สูตร: WPM * (Accuracy / 100) * 10 
        """
        stats = self.get_current_stats()
        final_score = stats["wpm"] * (stats["accuracy"] / 100) * 10
        return round(final_score)
        
    def finalize_session(self):
        """จบการพิมพ์ สรุปผลเพื่อเตรียมส่งบันทึกลง Oracle Database"""
        if self._is_completed:
            return None # ป้องกันการส่งผลซ้ำ (Replay Attack)
            
        self._end_time = datetime.now()
        self._is_completed = True
        
        stats = self.get_current_stats()
        stats["score"] = self.calculate_score()
        return stats