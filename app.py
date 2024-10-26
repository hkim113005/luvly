from flask import Flask, render_template, request, session, redirect, url_for, send_from_directory, jsonify
from flask_session import Session
from flask_cors import CORS

import time
from geopy.distance import geodesic

import sqlite3

from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)
CORS(app)

app.config["SESSION_TYPE"] = "filesystem"

Session(app)


DISTANCE = 20


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
    return render_template("home.html", user_id=session["user_id"], email=session["email"])


@app.route("/login", methods=["GET", "POST"])
@login_not_required
def login():
    session.clear()
    
    db = get_db()
    cursor = db.cursor()

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        user = cursor.fetchone()

        if len(user) == 0 or not check_password_hash(user[2], password):
            return render_template("login.html", email=email, password=password)

        session["user_id"] = user[0]
        session["email"] = email
        

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
    
        password = request.form.get("password")
        email = request.form.get("email")

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        if len(cursor.fetchall()) != 0:
            return "email repeat"

        cursor.execute("SELECT COUNT(*) FROM users")
        user_id = cursor.fetchone()[0]

        cursor.execute(f"""INSERT INTO users (user_id, email, password_hash) 
                       VALUES(SUBSTR('0000000000' || '{user_id}', -8, 8), '{email}', '{generate_password_hash(password)}');""")

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        user = cursor.fetchone()

        session["user_id"] = user[0]
        session["email"] = email

        
        db.commit()

        cursor.close()
        db.close()

        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/logout", methods=["GET"])
@login_required
def logout():
    session.clear()

    return redirect("/")


@app.route("/select", methods=["GET", "POST"])
@login_required
def select():
    if request.method == "POST":
        db = get_db()
        
        cursor = db.cursor()
    
        email = request.form.get("email")
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        if len(cursor.fetchall()) == 0:
            return "email does not exist"

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        luv = cursor.fetchone()

        user_id = session["user_id"]
        luv_id = luv[0]
            
        cursor.execute(f"""INSERT OR REPLACE INTO users_luvs (user_id, luv_id, date_time) 
                       VALUES(SUBSTR('0000000000' || '{user_id}', -8, 8), SUBSTR('0000000000' || '{luv_id}', -8, 8), '{date_time}');""")
        

        cursor.execute(f"DELETE FROM users_matches WHERE send_id = '{user_id}'")

        cursor.execute(f"""
                       SELECT user_id, latitude, longitude
                       FROM users_locations
                       WHERE user_id = '{user_id}'
                       ORDER BY date_time DESC
                       LIMIT 1;
                       """)
        send_id, send_latitude, send_longitude = cursor.fetchone()

        cursor.execute(f"""
                       SELECT user_id, latitude, longitude
                       FROM users_locations
                       WHERE user_id = '{luv_id}'
                       ORDER BY date_time DESC
                       LIMIT 1;
                       """)
        receive_id, receive_latitude, receive_longitude = cursor.fetchone()

        distance = geodesic((send_latitude, send_longitude), (receive_latitude, receive_longitude)).meters

        if distance < DISTANCE:
            # print(3)
            cursor.execute(f"INSERT OR REPLACE INTO users_matches (send_id, receive_id, distance, date_time) VALUES('{send_id}', '{receive_id}', '{distance}', '{date_time}')")


        db.commit()

        cursor.close()
        db.close()

        return redirect("/")

    else:
        return render_template("select.html")


@app.route("/get_users_matches", methods=["GET"])
@login_required
def get_users_matches():
    db = get_db()
        
    cursor = db.cursor()

    user_id = session["user_id"]

    cursor.execute(f"""
                   SELECT *
                   FROM users_matches
                   WHERE receive_id = '{user_id}'
                   """)
    
    results = cursor.fetchall()

    cursor.close()
    db.close()
    
    return results


@app.route("/update_location", methods=["POST"])
@login_required
def update_location():
    if request.method == "POST":
        db = get_db()
        cursor = db.cursor()
        
        data = request.get_json()[0]
        user_id = session["user_id"]
        
        latitude = data.get("latitude", None)
        longitude = data.get("longitude", None)
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(f"SELECT COUNT(*) FROM users_locations WHERE user_id = '{user_id}'")
        count = cursor.fetchone()[0]
        
        if count >= 30:
            cursor.execute(f"""
            DELETE FROM users_locations
            WHERE user_id = '{user_id}'
            AND date_time = (
                SELECT date_time
                FROM users_locations
                WHERE user_id = '{user_id}'
                ORDER BY date_time ASC
                LIMIT 1
            )
            """)
        cursor.execute(f"""
                       INSERT OR REPLACE INTO users_locations (user_id, latitude, longitude, date_time) 
                       VALUES ('{user_id}', '{latitude}', '{longitude}', '{date_time}')
                       """)

        
        # Calculate distances between users
        cursor.execute("""
                       SELECT user_id, latitude, longitude
                       FROM users_locations AS ul
                       WHERE date_time = (
                       SELECT MAX(date_time)
                       FROM users_locations
                       WHERE user_id = ul.user_id
                       )
                       """)
        
        all_users = cursor.fetchall()
        
        # # Delete existing entries for the current user in near_luvs
        cursor.execute(f"DELETE FROM users_matches WHERE receive_id = '{user_id}'")

        # print(all_users)
        for send_user in all_users:
            # print(send_user)
            send_id, send_latitude, send_longitude = send_user
            if send_id == user_id:
                continue  # Skip calculating distance to self
            
            distance = geodesic((latitude, longitude), (send_latitude, send_longitude)).meters
            
            # Store the calculated distance in the near_luvs table if less than 10 meters and the other user loves this user
            if distance < DISTANCE:
                cursor.execute(f"""
                               SELECT *
                               FROM users_luvs
                               WHERE user_id = '{send_id}'
                               ORDER BY date_time DESC
                               LIMIT 1;
                               """)
                
                match = cursor.fetchone()
                if match and match[2] == user_id:
                    # print(1)
                    cursor.execute(f"""
                                   INSERT OR REPLACE INTO users_matches (send_id, receive_id, distance, date_time)
                                   VALUES ('{send_id}', '{user_id}', '{distance}', '{date_time}')
                                   """)
        

        cursor.execute(f"DELETE FROM users_matches WHERE send_id = '{user_id}'")

        cursor.execute(f"SELECT * FROM users_luvs WHERE `user_id` = '{user_id}'")
        cursor.execute(f"""
                       SELECT *
                       FROM users_luvs
                       WHERE user_id = '{user_id}'
                       ORDER BY date_time DESC
                       LIMIT 1;
                       """)
        match = cursor.fetchone()
        if match and match[2] != user_id:
            receive_id = match[2]

            cursor.execute(f"""
                           SELECT user_id, latitude, longitude
                           FROM users_locations
                           WHERE user_id = '{user_id}'
                           ORDER BY date_time DESC
                           LIMIT 1;
            """)
            send_id, send_latitude, send_longitude = cursor.fetchone()

            cursor.execute(f"""
                           SELECT user_id, latitude, longitude
                           FROM users_locations
                           WHERE user_id = '{receive_id}'
                           ORDER BY date_time DESC
                           LIMIT 1;
                           """)
            receive_id, receive_latitude, receive_longitude = cursor.fetchone()

            distance = geodesic((send_latitude, send_longitude), (receive_latitude, receive_longitude)).meters
            date_time = time.strftime("%Y-%m-%d %H:%M:%S")

            if distance < DISTANCE:
                # print(2)
                cursor.execute(f"INSERT OR REPLACE INTO users_matches (send_id, receive_id, distance, date_time) VALUES('{send_id}', '{receive_id}', '{distance}', '{date_time}')")
                    
                
        db.commit()

        cursor.close()
        db.close()

        return jsonify(True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000, ssl_context="adhoc")