from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = "gizli-bir-key"  # Session için gerekli

DB_PATH = "feedback.db"

# Öğrenciye özel geri bildirimleri getir
def get_feedback_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT week, question_number, feedback
        FROM feedbacks
        WHERE email = ?
        ORDER BY week, question_number
    ''', (email,))
    rows = cursor.fetchall()
    conn.close()

    feedbacks = {}
    for week, question_number, feedback in rows:
        if week not in feedbacks:
            feedbacks[week] = []
        feedbacks[week].append((question_number, feedback))
    return feedbacks

# Tüm geri bildirimleri getir (admin için)
def get_all_feedback():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT email, week, question_number, feedback
        FROM feedbacks
        ORDER BY week, email, question_number
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

# -------------------- Öğrenci Girişi --------------------

@app.route('/', methods=["GET", "POST"])
@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form['email'].strip().lower()
        session['email'] = email
        return redirect(url_for('dashboard'))
    return render_template("login.html")

@app.route('/dashboard')
def dashboard():
    if 'email' not in session:
        return redirect(url_for('login'))

    email = session['email']
    feedbacks = get_feedback_by_email(email)
    return render_template("dashboard.html", email=email, feedbacks=feedbacks)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -------------------- Admin Girişi ve Panel --------------------

@app.route('/admin', methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        password = request.form['password'].strip()
        if password == "yzt1616":
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template("admin_login.html", error="Parola hatalı.")
    return render_template("admin_login.html")

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    feedbacks = get_all_feedback()
    return render_template("admin_dashboard.html", feedbacks=feedbacks)

@app.route('/admin/delete_all', methods=["POST"])
def delete_all_feedback():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM feedbacks")
    conn.commit()
    conn.close()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

# -------------------- Uygulama Başlat --------------------

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

