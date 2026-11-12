# 🚀 Typeclass - Project Setup Guide (สำหรับทีม Developer)

คู่มือนี้สำหรับสมาชิกในทีม (Backend, Teacher Feature หรือผู้ทดสอบ) ที่ต้องการ Clone โปรเจกต์นี้ไปพัฒนาต่อในเครื่องของตัวเอง

## 1. การเตรียมความพร้อม (Prerequisites)
* สิ่งที่ต้องมีในเครื่อง: **Python 3.8+** และ **Git**
* ขอข้อมูลไฟล์ `.env` (รหัสผ่าน Oracle Database และ JWT Secret Key) จากทีม

## 2. ขั้นตอนการติดตั้งและรันโปรเจกต์

**Step 1: Clone โปรเจกต์ และสลับไปยัง Branch ที่ต้องการทำงาน**
```bash
git clone https://github.com/Teamproject-SDD2-SEC1-2569/OOP-SDD2-type.git
cd OOP-SDD2-type
git checkout <ชื่อ-branch-ของคุณ>
```

**Step 2: สร้างและเปิดใช้งาน Virtual Environment**
เพื่อป้องกันไม่ให้แพ็กเกจของโปรเจกต์ตีกับระบบในเครื่อง

* **Windows:**
  ```bash
  python -m venv .venv
  .venv\Scripts\activate
  ```
* **Mac/Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

**Step 3: ติดตั้ง Libraries ที่จำเป็น**
```bash
pip install -r requirements.txt
```

**Step 4: ตั้งค่าตัวแปรสภาพแวดล้อม (Environment Variables)**
เนื่องจากไฟล์ `.env` ถูก Ignore ไว้เพื่อความปลอดภัย ให้สร้างไฟล์ชื่อ `.env` ไว้ที่โฟลเดอร์นอกสุด (ระดับเดียวกับ `run.py`) และใส่ข้อมูลดังนี้:

```env
# ตั้งค่า Oracle Database (สอบถาม Password จากทีม Database)
ORACLE_DB_USER=WEB_APP_USER
ORACLE_DB_PASSWORD=your_password_here
ORACLE_DB_DSN=(description= (retry_count=20)(retry_delay=3)(address=(protocol=tcps)(port=1522)(host=adb.ap-singapore-1.oraclecloud.com))(connect_data=(service_name=gce18b24390782a_typeclass_medium.adb.oraclecloud.com))(security=(ssl_server_dn_match=yes)))

# ตั้งค่าความปลอดภัยสำหรับ Flask และ JWT
SECRET_KEY=typeclass-super-secret-key
JWT_SECRET_KEY=typeclass-jwt-secret-key
```

**Step 5: รันเซิร์ฟเวอร์**
```bash
python run.py
```
เซิร์ฟเวอร์จะรันที่ `http://127.0.0.1:5000` สามารถเปิดดูในเบราว์เซอร์ได้ทันที

---

## 📂 3. โครงสร้างโปรเจกต์ (Project Structure)

```text
OOP-SDD2-type/
├── app/
│   ├── __init__.py              # Application Factory (create_app) ตั้งค่า Flask, CORS, JWT, SocketIO
│   ├── config.py                # โหลดค่าตัวแปรจาก .env (SECRET_KEY, Oracle DB, Anti-cheat)
│   ├── database.py              # ฟังก์ชัน get_db_connection() เชื่อมต่อ Oracle Cloud Database
│   │
│   ├── models/                  # 📦 [Model Layer] คลาส OOP และโครงสร้างข้อมูล
│   │   ├── __init__.py
│   │   ├── domain.py            # OOP Entities: User, Student, Teacher, Classroom, SubmissionResult
│   │   └── typing_session.py    # BaseTypingMode (Abstract) และ StandardTypingSession (คำนวณ WPM/Score)
│   │
│   ├── services/                # ⚙️ [Service / Business Logic Layer]
│   │   ├── __init__.py
│   │   └── typing_service.py    # TypingService: จัดการ Session, ห้องเรียน, Leaderboard และ Anti-Cheat
│   │
│   ├── routes/                  # 🌐 [Controller / HTTP Presentation Layer]
│   │   ├── __init__.py
│   │   ├── auth_routes.py       # API สมัครสมาชิก (/auth/register) และเข้าสู่ระบบ (/auth/login)
│   │   ├── student_routes.py    # Route หน้าเว็บฝั่งนักเรียน (/, /classroom, /typing, /progress, /history)
│   │   └── teacher_routes.py    # Route และ API ฝั่งอาจารย์ (/teacher/dashboard, สร้างห้อง, ดูสถิติ)
│   │
│   ├── sockets/                 # ⚡ [Real-time WebSocket Layer]
│   │   ├── __init__.py
│   │   └── events.py            # Socket.IO Events: connect, join_classroom, start_typing, keystroke, submit_score
│   │
│   ├── utils/                   # 🛠️ [Utilities & Helpers]
│   │   ├── __init__.py
│   │   ├── auth_utils.py        # Decorator @require_role ตรวจสอบสิทธิ์ JWT (Student / Teacher)
│   │   └── constants.py         # คลังคำศัพท์ (GENERAL_WORDS, CODING_WORDS) และ MAX_WPM_THRESHOLD
│   │
│   ├── templates/               # 🎨 [Frontend HTML Templates]
│   │   ├── student/             # หน้าเว็บฝั่งนักเรียน (login, register, join, classroom, typing, progress, ฯลฯ)
│   │   └── teacher/             # หน้าเว็บฝั่งอาจารย์ (Dashboard, Manage-Classroom, create-room, menu)
│   │
│   ├── static/                  # 💅 [Static Assets]
│   │   └── css/
│   │       └── style.css        # ไฟล์ CSS หลักของระบบ
│   │
│   ├── test/                    # 🧪 [Unit Tests]
│   │   ├── __init__.py
│   │   └── test_basic.py        # ทดสอบ OOP Models, การคำนวณ WPM/Accuracy และระบบ Anti-Cheat
│   │
│   └── (Compatibility Shims)    # ไฟล์เชื่อมโยงชื่อเดิมเพื่อไม่ให้โค้ดเก่าพัง (models.py, route.py, teacher_routes.py, ฯลฯ)
│
├── docs/                        # 📚 เอกสารคู่มือของทีม
│   ├── SETUP_GUIDE.md           # คู่มือการติดตั้งและรันโปรเจกต์
│   ├── checklest.md             # รายการตรวจสอบงาน (Checklist)
│   └── websocket_api_spec.md    # ข้อกำหนดการรับ-ส่งข้อมูลผ่าน WebSocket
│
├── .env                         # 🔐 ไฟล์เก็บค่าความลับ (Database Password, Secret Keys) *ไม่ขึ้น Git*
├── .gitignore                   # ไฟล์กำหนดรายการที่ไม่ให้นำขึ้น Git (.venv, .env, __pycache__)
├── requirements.txt             # รายชื่อแพ็กเกจ Python ทั้งหมดที่ใช้ในโปรเจกต์
├── run.py                       # 🚀 ไฟล์หลักสำหรับรันเซิร์ฟเวอร์จริง (Flask + Socket.IO)
├── app.py                       # ไฟล์สำรองสำหรับรันดูเฉพาะหน้าเว็บ HTML เบื้องต้น
└── test_client.py               # สคริปต์จำลอง Client สำหรับทดสอบยิง WebSocket
```

### 💡 สรุปการแบ่งงานตามโฟลเดอร์สำหรับสมาชิกในทีม
* **ทีม Frontend (UI/UX):** แก้ไขไฟล์ใน `app/templates/student/`, `app/templates/teacher/` และ `app/static/css/style.css`
* **ทีม Backend (API & Auth):** แก้ไขไฟล์ใน `app/routes/` (`auth_routes.py`, `student_routes.py`, `teacher_routes.py`)
* **ทีม Real-time & Typing Logic (OOP):** แก้ไขไฟล์ใน `app/models/` (`domain.py`, `typing_session.py`), `app/services/` (`typing_service.py`) และ `app/sockets/` (`events.py`)
* **ทีม Database:** แก้ไขการเชื่อมต่อใน `app/database.py` และคำสั่ง SQL ใน `app/routes/` หรือ `app/services/`