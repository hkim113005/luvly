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
    return render_template("home.html", user_id=session["user_id"], username=session["username"])


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

        if len(user) == 0 or not check_password_hash(user[0][5], password):
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
@login_required
def logout():
    session.clear()

    return redirect("/")


@app.route("/update_location", methods=["POST"])
@login_required
def update_location():
    if request.method == "POST":
        db = sqlite3.connect("data.db")
        
        cursor = db.cursor()
        
        data = request.get_json()[0]
        user_id = session["user_id"]
        
        latitude = data.get("latitude", None)
        longitude = data.get("longitude", None)
      
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("SELECT COUNT(*) FROM user_locations WHERE user_id = ?", (user_id,))
        count = cursor.fetchone()[0]
        
        if count >= 30:
            cursor.execute("""
            DELETE FROM user_locations
            WHERE user_id = ?
            AND date_time = (
                SELECT date_time
                FROM user_locations
                WHERE user_id = ?
                ORDER BY date_time ASC
                LIMIT 1
            )
            """, (user_id, user_id))
        
        cursor.execute("""
            INSERT INTO user_locations (user_id, latitude, longitude, date_time) 
            VALUES (?, ?, ?, ?)
        """, (user_id, latitude, longitude, date_time))
        
        db.commit()

        results = {"processed": "true"}
        
        # Calculate distances between users
        cursor.execute("""
            SELECT user_id, latitude, longitude 
            FROM user_locations 
            WHERE (user_id, date_time) IN (
                SELECT user_id, MAX(date_time) 
                FROM user_locations 
                GROUP BY user_id
            )
        """)
        all_users = cursor.fetchall()
        
        # # Delete existing entries for the current user in near_luvs
        cursor.execute("DELETE FROM near_luvs WHERE user_id = ?", (session["user_id"],))
        db.commit()
        # print(all_users)
        for other_user in all_users:
            other_id, other_lat, other_lon = other_user
            if other_id == user_id:
                continue  # Skip calculating distance to self
            
            distance = geodesic((latitude, longitude), (other_lat, other_lon)).meters
            
            # Store the calculated distance in the near_luvs table if less than 10 meters and the other user loves this user
            if distance < 100:
                cursor.execute("SELECT * FROM user_luvs WHERE user_id = ? AND luv_id = ?", (other_id, user_id))
                if cursor.fetchone():
                    cursor.execute("""
                        INSERT OR REPLACE INTO near_luvs (user_id, luv_id, distance, date_time)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, other_id, distance, date_time))
            else:
                # Check if the user-other pair exists in near_luvs
                cursor.execute("""
                    SELECT * FROM near_luvs 
                    WHERE user_id = ? AND luv_id = ?
                """, (user_id, other_id))
                if cursor.fetchone():
                    # If the pair exists, remove it
                    cursor.execute("""
                        DELETE FROM near_luvs 
                        WHERE user_id = ? AND luv_id = ?
                    """, (user_id, other_id))
                    
            
        results["distances_calculated"] = "true"
                
        db.commit()

        cursor.close()
        db.close()

        return jsonify(results)


@app.route("/select", methods=["GET", "POST"])
@login_required
def select():
    if request.method == "POST":
        db = get_db()
        
        cursor = db.cursor()
    
        email = request.form.get("email")
        # first_name = request.form.get("first_name")
        # last_name = request.form.get("last_name")
        # dob = request.form.get("dob")
        # sex = request.form.get("sex")
        # grade = request.form.get("grade")
        # type = request.form.get("type")
        # organization = request.form.get("organization")

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        if len(cursor.fetchall()) == 0:
            return "email does not exist"

        cursor.execute(f"SELECT * FROM users WHERE email = '{email}'")
        luv = cursor.fetchall()

        user_id = session["user_id"]
        luv_id = luv[0][0]
        # username = user[0][1]
        # ser_name = user[0][2]

        cursor.execute(f"SELECT * FROM user_luvs WHERE `user_id` = '{user_id}'")

        if len(cursor.fetchall()) == 0:
            cursor.execute(f"""INSERT INTO user_luvs (user_id, luv_id) 
                           VALUES(substr('0000000000' || '{user_id}', -8, 8), substr('0000000000' || '{luv_id}', -8, 8));""")
        else:
            cursor.execute(f"""UPDATE user_luvs
                           SET luv_id = '{luv_id}'
                           WHERE user_id = '{user_id}'""")
        db.commit()

        cursor.close()
        db.close()

        return redirect("/")

    else:
        return render_template("select.html")


@app.route("/get_near_luvs", methods=["GET"])
@login_required
def get_near_luvs():
    db = get_db()
        
    cursor = db.cursor()

    user_id = session["user_id"]

    cursor.execute(f"""WITH RankedLuvs AS (
                        SELECT 
                            user_id, 
                            luv_id, 
                            distance,
                            date_time,
                            ROW_NUMBER() OVER (PARTITION BY luv_id ORDER BY date_time DESC) AS rn
                        FROM near_luvs
                        WHERE user_id = '{user_id}')
                    SELECT 
                        user_id, 
                        luv_id, 
                        distance,
                        date_time
                    FROM RankedLuvs
                    WHERE rn = 1;""")
    results = cursor.fetchall()

    cursor.close()
    db.close()
    
    return results


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1000, ssl_context='adhoc')