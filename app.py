from flask import Flask, render_template

app = Flask(__name__)

# 1. หน้าเข้าสู่ระบบ (Login)
@app.route('/')
@app.route('/login')
@app.route('/login.html')
def login():
    return render_template('student/login.html')

# 2. หน้าสมัครสมาชิก (Register)
@app.route('/register')
@app.route('/register.html')
def register():
    return render_template('student/register.html')

# 3. หน้าห้องเรียน (Classroom)
@app.route('/classroom')
@app.route('/classroom.html')
def classroom():
    return render_template('student/classroom.html')

# 4. หน้าพัฒนาการ (Progress)
@app.route('/progress')
@app.route('/progress.html')
def progress():
    return render_template('student/progress.html')

# 5. หน้าประวัติการพิมพ์ (Typing History)
@app.route('/typing_history')
@app.route('/typing_history.html')
def typing_history():
    return render_template('student/typing_history.html')

# 6. หน้าฝึกพิมพ์ (Typing)
@app.route('/typing')
@app.route('/typing.html')
def typing():
    return render_template('student/typing.html')

# 7. หน้าผลการพิมพ์ (Typing Result)
@app.route('/typing-result')
@app.route('/typing-result.html')
def typing_result():
    return render_template('student/typing-result.html')

if __name__ == '__main__':
    app.run(debug=True)