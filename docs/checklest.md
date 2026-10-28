ส่วนที่ 1: การเตรียมเนื้อหาฝั่ง อ.ไพบูลย์ (OOP, Architecture & Collaboration)

[ ] สไลด์บทนำและขอบเขต (Scope & Capabilities):

สรุปปัญหาที่ทำให้เกิดโปรเจกต์นี้ และวัตถุประสงค์

ระบุ Scope ชัดเจน เช่น "ระบบแยก Role (Teacher/Student) ด้วย Login เดียว", "ระบบ Real-time Leaderboard", "การเซฟประวัติลง Oracle DB"

[ ] สไลด์ Architecture & Class Diagram (สำคัญ 30%):

วาด Component Diagram หรือ Layered Architecture (แสดงฝั่ง Client (HTML/JS) -> Server (Flask/Socket.IO) -> Database (Oracle)).

วาด Class Diagram โฟกัสความสัมพันธ์หลักๆ

🌟 ไฮไลต์โค้ด (SOLID Principles): ยกตัวอย่างไฟล์ models.py ที่คุณมีคลาส BaseTypingMode และให้ StandardTypingSession สืบทอดมา (Inheritance/Polymorphism) นี่คือตัวอย่างที่ชัดเจนของ O (Open/Closed Principle) ที่ระบบพร้อมขยายโหมดการพิมพ์อื่นๆ ได้ในอนาคตโดยไม่ต้องแก้คลาสหลัก

[ ] สไลด์ Team Collaboration (Git Workflow) (15%):

แคปเจอร์หน้าจอประวัติการ Commit จาก GitHub (เช่น Branch feature/backend-teacher และ Frontend-student ที่มารวมกันใน dev)

โชว์รูปแบบการตั้งชื่อ Commit ที่มีความหมาย (เช่น feat:, docs:, merge:)

🌟 จุดขายตอนพรีเซนต์: เล่าถึงตอนที่แก้ Merge Conflict ในไฟล์ database.py เพื่อแสดงให้เห็นถึงการทำงานร่วมกันและการทำ Code Review ภายในทีม

[ ] เตรียมความพร้อม Live Demo & Code Quality (40%):

ซ้อมรันโปรแกรมให้ราบรื่นตั้งแต่: สมัคร/ล็อกอิน -> ครูสร้างห้อง -> นักเรียนเข้าห้อง -> พิมพ์โชว์ Leaderboard -> บันทึกคะแนนลงฐานข้อมูล

🌟 จุดขายเรื่อง Exception Handling (Data Flow): โชว์บล็อกโค้ด try...except...finally ใน route.py ตรงจังหวะเชื่อมต่อ Oracle DB ที่ป้องกันเซิร์ฟเวอร์พังเมื่อ DB มีปัญหา

🌟 จุดขายเรื่อง Edge Case พื้นฐาน: เล่าถึงการดัก Anti-Cheat (WPM > 320) ที่เพิ่งใส่เข้าไปในโค้ด

ส่วนที่ 2: การเตรียมเนื้อหาฝั่ง อ.สุระชัย (Security, Threat & CI/CD)

[ ] สไลด์ Threat Analysis & Risk Register (30%):

วาด DFD (Data Flow Diagram) แสดงทิศทางข้อมูลตอน Login และส่งผลพิมพ์ (Socket.IO).

เขียน Misuse Case (เช่น นักเรียนปลอมแปลงคะแนน (WPM), คนนอกเข้าห้องพิมพ์โดยไม่มีรหัส).

ลิสต์ Assets (เช่น ข้อมูลนักเรียน, JWT Token, รหัสผ่าน, Oracle Database).

กำหนด Security Requirements และทำ Risk Register เป็นตาราง (ความเสี่ยง, โอกาสเกิด, ผลกระทบ, วิธีรับมือ).

[ ] สไลด์ Secure Coding & Refactoring (20%):

🌟 จุดขายที่ 1 (SQL Injection Prevention): โชว์โค้ดใน route.py ที่ใช้ Parameterized Query (VALUES (:1, :2, ...)) แทนการต่อ String เพื่อป้องกัน SQL Injection

🌟 จุดขายที่ 2 (Authentication & Refactor): อธิบายการรีแฟกเตอร์นำ flask-jwt-extended มาใช้ยืนยันตัวตน (Token-based) แทนการใช้ Session แบบเก่า เพื่อเพิ่มความปลอดภัยและรองรับการขยายสเกล

[ ] ตาราง Traceability Matrix (10%):

สร้างตารางเชื่อมโยงว่า Requirement ข้อไหน -> ถูกออกแบบใน Class/Diagram ไหน -> ไปอยู่ในโค้ดไฟล์ไหน (เช่น ฟังก์ชันเก็บคะแนน -> Class Diagram ตาราง Submission_Results -> ฟังก์ชัน handle_submit_score())

[ ] การติดตั้งอัตโนมัติ CI/CD (40%):

(อันนี้คุณต้องเซ็ตอัปเพิ่ม) แนะนำให้ใช้ GitHub Actions เขียนไฟล์ .yml เพื่อทำกระบวนการ CI (Continuous Integration): ตรวจสอบ PEP8 หรือรัน Automated Tests ทันทีที่มีการ Push โค้ด

ทำกระบวนการ CD (Continuous Deployment): ตั้งค่าให้โค้ดถูก Deploy ไปยัง Server จริง (เช่น อัปเดตขึ้น Oracle Cloud, Heroku, หรือ PythonAnywhere อัตโนมัติเมื่อ Merge ลง Branch หลัก) พร้อมแคปภาพผลลัพธ์การติดตั้งโชว์อาจารย์