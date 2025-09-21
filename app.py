from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from mysql.connector import errorcode
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = "replace-with-a-secure-random-secret-key"


# MySQL configuration
db_config = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',  #username 
    'password': 'Satyam#9235',
    'database': 'Personal_info' 
}


def get_db_connection():
    """Create and return a new MySQL connection using db_config."""
    return mysql.connector.connect(**db_config)


def ensure_database_exists() -> None:
    """Create the database if it doesn't already exist."""
    try:
        conn = mysql.connector.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {db_config['database']} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
    except mysql.connector.Error as err:
        print(f"Error ensuring database exists: {err}")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


def ensure_users_table_exists() -> None:
    """Create the users table if it doesn't already exist."""
    create_table_sql = (
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL UNIQUE,
            age INT NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    )
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        conn.commit()
    except mysql.connector.Error as err:
        # Optionally flash/log in real scenarios
        print(f"Error ensuring table exists: {err}")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        age = request.form.get("age", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not age or not password:
            flash("All fields are required.", "error")
            return redirect(url_for("signup"))

        try:
            age_int = int(age)
        except ValueError:
            flash("Age must be a valid number.", "error")
            return redirect(url_for("signup"))

        password_hash = generate_password_hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            insert_sql = (
                "INSERT INTO users (name, email, age, password_hash) VALUES (%s, %s, %s, %s)"
            )
            cursor.execute(insert_sql, (name, email, age_int, password_hash))
            conn.commit()
            flash("Registration successful. Please sign in.", "success")
            return redirect(url_for("signin"))
        except mysql.connector.IntegrityError:
            flash("Email already registered.", "error")
            return redirect(url_for("signup"))
        except mysql.connector.Error as err:
            print(f"Signup DB error: {err}")
            flash("An error occurred. Please try again.", "error")
            return redirect(url_for("signup"))
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("signin"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            select_sql = "SELECT id, name, email, age, password_hash FROM users WHERE email = %s LIMIT 1"
            cursor.execute(select_sql, (email,))
            user = cursor.fetchone()
            if not user or not check_password_hash(user["password_hash"], password):
                flash("Invalid email or password.", "error")
                return redirect(url_for("signin"))

            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            return redirect(url_for("dashboard"))
        except mysql.connector.Error as err:
            print(f"Signin DB error: {err}")
            flash("An error occurred. Please try again.", "error")
            return redirect(url_for("signin"))
        finally:
            try:
                cursor.close()
                conn.close()
            except Exception:
                pass

    return render_template("signin.html")


def login_required(view_func):
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("signin"))
        return view_func(*args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


@app.route("/dashboard")
@login_required
def dashboard():
    users = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, age, created_at FROM users ORDER BY created_at DESC")
        users = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Dashboard DB error: {err}")
        flash("Unable to load users.", "error")
    finally:
        try:
            cursor.close()
            conn.close()
        except Exception:
            pass
    return render_template("dashboard.html", users=users)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# Ensure database and table exist on module import (Flask 3+ removed before_first_request)
try:
    ensure_database_exists()
    ensure_users_table_exists()
except Exception as e:
    print(f"Initialization error: {e}")


if __name__ == "__main__":
    app.run(debug=True)
