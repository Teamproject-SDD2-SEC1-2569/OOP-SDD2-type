from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

# 1. หน้าเข้าสู่ระบบ (หน้าแรก)
@app.route('/')
@app.route('/login')
@app.route('/login.html')
def login():
    return render_template('login.html')

# 2. หน้าสมัครสมาชิก
@app.route('/register')
@app.route('/register.html')
def register():
    return render_template('register.html')

# 3. หน้าห้องเรียน
@app.route('/classroom')
@app.route('/classroom.html')
def classroom():
    return render_template('classroom.html')

# 4. หน้าพัฒนาการ
@app.route('/progress')
@app.route('/progress.html')
def progress():
    return render_template('progress.html')

# 5. หน้าประวัติการพิมพ์
@app.route('/typing_history')
@app.route('/typing_history.html')
def typing_history():
    return render_template('typing_history.html')

# 6. หน้าฝึกพิมพ์
@app.route('/typing')
@app.route('/typing.html')
def typing():
    return render_template('typing.html')

# 7. หน้าผลการพิมพ์
@app.route('/typing-result')
@app.route('/typing-result.html')
def typing_result():
    return render_template('typing-result.html')

if __name__ == '__main__':
    app.run(debug=True)