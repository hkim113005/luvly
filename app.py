from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory, jsonify
from flask_session import Session

import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)

app.config["SESSION_TYPE"] = "filesystem"

Session(app)

def get_db():
    return sqlite3.connect("data.db")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def login_not_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is not None:
            return redirect("/")
        else:
            return f(*args, **kwargs)
    return decorated_function

@app.route("/", methods=["GET"])
@login_required
def home():
    return "Hello"


@app.route("/login", methods=["GET", "POST"])
@login_not_required
def login():
    session.clear()
    
    db = get_db()
    
    cursor = db.cursor()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        cursor.execute(f"SELECT * FROM users WHERE username = '{username}' OR email = '{username}'")
        user = cursor.fetchall()

        if len(user) == 0 or not check_password_hash(user[0][9], password):
            return render_template("login.html", username=username, password=password)

        session["user_id"] = user[0][0]
        session["username"] = user[0][1]
        session["user_name"] = user[0][2]
        
        cursor.close()
        db.close()

        return redirect("/")
    else:
        cursor.close()
        db.close()
        
        return render_template("login.html")


@app.route("/sign-up", methods=["GET", "POST"])
@login_not_required
def register():
    if request.method == "POST":
        db = get_db()
        
        cursor = db.cursor()
    
        username = request.form.get("username")
        password = request.form.get("password")
        email = request.form.get("email")
        # first_name = request.form.get("first_name")
        # last_name = request.form.get("last_name")
        # dob = request.form.get("dob")
        # sex = request.form.get("sex")
        # grade = request.form.get("grade")
        # type = request.form.get("type")
        # organization = request.form.get("organization")

        cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
        if len(cursor.fetchall()) != 0:
            return "user repeat"

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        if len(cursor.fetchall()) != 0:
            return "email repeat"

        cursor.execute("SELECT COUNT(*) FROM users")
        user_id = cursor.fetchall()[0][0]

        cursor.execute(f"INSERT INTO users (user_id, username, email, password_hash) VALUES(substr('0000000000' || '{user_id}', -8, 8), '{username}', '{email}', '{generate_password_hash(password)}');")
        db.commit()

        cursor.execute(f"SELECT * FROM users WHERE username = '{username}'")
        user = cursor.fetchall()

        session["user_id"] = user[0][0]
        session["username"] = user[0][1]

        cursor.close()
        db.close()

        return redirect("/")

    else:
        return render_template("register.html")

@app.route("/logout", methods=["GET"])
@login_not_required
def logout():
    session.clear()

    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000)