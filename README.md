# Typeclass ⌨️
**ระบบห้องเรียนฝึกพิมพ์ดีด (Typing Skill Assessment for Classroom)**

โครงงานนี้เป็นส่วนหนึ่งของรายวิชา Software Design and Development 2 เสนอ ผศ.สุระชัย พิมพ์สาลี โดยเป็นแพลตฟอร์มจัดการการฝึกพิมพ์ดีดภาษาอังกฤษที่ออกแบบมาสำหรับชั้นเรียนโดยเฉพาะ มุ่งเน้นให้อาจารย์เป็นผู้จัดการคลาสเรียนและเป็นเจ้าของข้อมูลอย่างแท้จริง

---

## 📌 1. ที่มาและความสำคัญ (Problem Statement)
ระบบพิมพ์ดีดที่มีอยู่ในปัจจุบันมุ่งเน้นการฝึกทำแบบทดสอบหรือการจัดอันดับผู้เล่นทั่วไป ซึ่งไม่ตอบโจทย์การใช้งานในห้องเรียนจริง ทำให้เกิดปัญหาดังนี้:
* อาจารย์ไม่มีข้อมูลผลการพิมพ์จริงของนักเรียน
* เกิดช่องโหว่ในการทุจริตคะแนนและการแจ้งคะแนนเท็จ
* อาจารย์ตรวจสอบและติดตามผลการพัฒนาของนักเรียนได้ยาก[cite: 1]
* ข้อมูลการพิมพ์ไม่ได้ถูกเก็บอย่างเป็นระบบ[cite: 1]

---

## 🎯 2. วัตถุประสงค์ของโครงงาน (Objectives)
* **โปร่งใส:** รวมข้อมูลสถิติไว้ที่อาจารย์โดยตรง ป้องกันนักเรียนโกงคะแนน[cite: 1]
* **ฝีมือจริง:** วิเคราะห์พัฒนาการและจุดอ่อนผ่าน Dashboard แทนการถามคะแนนปากเปล่า[cite: 1]
* **ลดภาระ:** ประเมินผลและจัดอันดับคะแนนผู้เรียนอัตโนมัติ ช่วยลดเวลาการตรวจคะแนนของอาจารย์[cite: 1]
* **ยืดหยุ่น:** ประยุกต์ใช้หลักการ Object-Oriented Programming (OOP) เพื่อให้ระบบมีประสิทธิภาพและดูแลรักษาง่าย[cite: 1]

---

## ✨ 3. ฟีเจอร์การทำงานหลัก (Key Features)

### 👨‍🏫 ระบบสำหรับผู้สอน (Teacher Portal)
* **Classroom Management:** สร้างห้องแข่งขัน เปิด/ปิดห้อง และออกรหัสเชิญ (Invite Code)[cite: 1]
* **Analytics Dashboard:** วิเคราะห์สถิติภาพรวมของห้องเรียน เช่น ความเร็ว (WPM) และความแม่นยำ (Accuracy)[cite: 1]
* **Individual Tracking:** แสดงกราฟติดตามพัฒนาการของนักเรียนรายบุคคลในระยะสั้นและระยะยาว[cite: 1]

### 🧑‍🎓 ระบบสำหรับผู้เรียน (Student Portal)
* **Interactive Typing Arena:** สนามฝึกพิมพ์พร้อมคีย์บอร์ดจำลองที่เปลี่ยนสีตอบสนองการกดแบบ Real-time[cite: 1]
* **Performance Tracking:** บันทึกและแสดงสถิติความเร็วสูงสุดส่วนตัว (Personal Best)[cite: 1]
* **Classroom Leaderboard:** แสดงตารางจัดอันดับนักเรียนเฉพาะภายในห้องเรียนเดียวกันเพื่อสร้างแรงจูงใจ[cite: 1]

---

## 🏗️ 4. สถาปัตยกรรมระบบ (System Architecture)
ระบบแบ่งการทำงานเป็นส่วนอย่างชัดเจน เพื่อให้ง่ายต่อการพัฒนาและบำรุงรักษา[cite: 1]
* **Client Side:** นักเรียนและอาจารย์ใช้งานผ่าน Web Browser เพื่อรับคำสั่งและแสดงผล[cite: 1]
* **Server Side:** ทำหน้าที่ตรวจคำ จับเวลา คำนวณ WPM, Accuracy, Score และจัดการระบบทั้งหมด[cite: 1]
* **Database:** จัดเก็บข้อมูลผู้ใช้ ข้อมูลห้องเรียน ผลการพิมพ์ และประวัติเชิงลึก[cite: 1]

---

## 💻 5. เครื่องมือและเทคโนโลยี (Technology Stack)
* **Frontend:** HTML, CSS, Bootstrap[cite: 1]
* **Backend:** Python, Flask (พัฒนาระบบตามหลัก OOP)[cite: 1]
* **Database:** Oracle Database (บนระบบ Cloud)[cite: 1]

---

## 🚧 6. ขอบเขตของโครงงาน (Project Scope)
**สิ่งที่ไม่อยู่ในขอบเขต (Out of Scope):**
* การพัฒนาเป็นแอปพลิเคชันบนสมาร์ทโฟน (Mobile Application)[cite: 1]
* ระบบการแข่งขันจับคู่แบบเรียลไทม์ข้ามห้องเรียน (Global Multiplayer)[cite: 1]
* การรองรับชุดข้อความทดสอบภาษาอื่นๆ นอกเหนือจากภาษาอังกฤษ[cite: 1]

---

## 🚀 7. การติดตั้งและเริ่มต้นใช้งาน (Getting Started)

**1. โคลนโปรเจกต์**
```bash
git clone https://github.com/Teamproject-SDD2-SEC1-2569/OOP-SDD2-type.git
cd OOP-SDD2-type
```

**2. สร้าง Virtual Environment และติดตั้งแพ็กเกจ**
```bash
# Mac/Linux
python3 -m venv .venv
source .venv/bin/activate

# Windows
python -m venv .venv
.venv\Scripts\activate

# ติดตั้ง Libraries
pip install -r requirements.txt
```

**3. ตั้งค่าไฟล์ `.env` และรันเซิร์ฟเวอร์**
สร้างไฟล์ `.env` ที่โฟลเดอร์หลัก (ดูรายละเอียดใน [`docs/SETUP_GUIDE.md`](docs/SETUP_GUIDE.md)) แล้วรัน:
```bash
python run.py
```
เปิดใช้งานผ่านเบราว์เซอร์ที่ `http://127.0.0.1:5001` (หรือ `http://localhost:5001`)

---

## 📚 เอกสารประกอบโครงการ (Documentation)
* [🎓 เอกสารสรุปเนื้อหาโครงงานสำหรับการประเมินผล อ.ไพบูลย์ (Presentation Guide)](docs/PRESENTATION_SDD2_PAIBOON.md)
* [📘 คู่มือโครงสร้างระบบและฟังก์ชันฉบับละเอียด (Project Structure & Function Reference)](docs/PROJECT_STRUCTURE_AND_FUNCTION_REFERENCE.md)
* [🗄️ แผนภาพฐานข้อมูล ER Diagram และ Data Dictionary (Oracle Cloud Database)](docs/oracle_database_erd.md)
* [⚡ เอกสารระบบ WebSocket Real-time API Specification](docs/websocket_api_spec.md)
* [🛠️ คู่มือการติดตั้งและทดสอบระบบ (Setup Guide)](docs/SETUP_GUIDE.md)

---

## 📂 8. โครงสร้างโปรเจกต์ (Project Structure)

```text
OOP-SDD2-type/
├── app/
│   ├── __init__.py              # Application Factory (create_app) ตั้งค่า Flask, CORS, JWT, SocketIO
│   ├── config.py                # โหลดค่าตัวแปรจาก .env (SECRET_KEY, Oracle DB, Anti-cheat)
│   ├── database.py              # ฟังก์ชัน get_db_connection() เชื่อมต่อ Oracle Cloud Database
│   ├── models/                  # 📦 [Model Layer] OOP Entities (domain.py) และ Session (typing_session.py)
│   ├── services/                # ⚙️ [Service Layer] Business Logic (typing_service.py)
│   ├── routes/                  # 🌐 [Controller Layer] HTTP Routes (auth, student, teacher)
│   ├── sockets/                 # ⚡ [Real-time Layer] WebSocket Events (events.py)
│   ├── utils/                   # 🛠️ [Utilities] Auth Decorators และคลังคำศัพท์
│   ├── templates/               # 🎨 [Frontend HTML] หน้าเว็บ student/ และ teacher/
│   ├── static/                  # 💅 [Static Assets] ไฟล์ CSS (style.css)
│   └── test/                    # 🧪 [Unit Tests] ชุดทดสอบระบบ (test_basic.py)
├── docs/                        # 📚 เอกสารคู่มือของทีม (SETUP_GUIDE.md, websocket_api_spec.md)
├── requirements.txt             # รายชื่อแพ็กเกจ Python
└── run.py                       # 🚀 ไฟล์หลักสำหรับรันเซิร์ฟเวอร์
```
