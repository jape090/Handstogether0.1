"""Flask website with a local SQLite database."""

import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path

from flask import Flask, abort, jsonify, request, send_from_directory, session


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "hands_together.db"
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("HANDS_TOGETHER_SECRET", "local-development-key-change-before-deployment"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)

PAGES = {
    "index.html": "index.html", "signup": "signup.html", "signup.html": "signup.html",
    "login": "login.html", "login.html": "login.html", "found": "found.html",
    "found.html": "found.html", "volunteer": "volunteer.html", "volunteer.html": "volunteer.html",
}
ASSETS = {"styles.css", "app.js"}


def connect_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


@contextmanager
def database():
    db = connect_db()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    with database() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                account_type TEXT NOT NULL DEFAULT 'Community member',
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('lost','found','missing')),
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                report_date TEXT NOT NULL,
                location TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'published',
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS volunteer_signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity TEXT NOT NULL,
                full_name TEXT NOT NULL,
                contact TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );
        """)


def now_iso():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def json_error(message, status=400):
    return jsonify({"error": message}), status


@app.get("/")
@app.get("/home")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/<path:page>")
def page_or_asset(page):
    if page in PAGES:
        return send_from_directory(BASE_DIR, PAGES[page])
    if page in ASSETS:
        return send_from_directory(BASE_DIR, page)
    abort(404)


@app.post("/api/signup")
def signup():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    phone = str(data.get("phone", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    account_type = str(data.get("accountType", "Community member")).strip()
    password = str(data.get("password", ""))
    if not name or not phone or not email or len(password) < 8:
        return json_error("Enter your name, phone, email, and a password with at least 8 characters.")
    if account_type not in {"Community member", "Organization"}:
        account_type = "Community member"
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    try:
        with database() as db:
            db.execute("INSERT INTO users(full_name,phone,email,account_type,password_hash,password_salt,created_at) VALUES(?,?,?,?,?,?,?)",
                       (name, phone, email, account_type, password_hash.hex(), salt.hex(), now_iso()))
            user_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    except sqlite3.IntegrityError:
        return json_error("That email or phone number is already registered.", 409)
    session.clear()
    session["user_id"] = user_id
    session["user_name"] = name
    return jsonify({"message": "Your account was created.", "name": name}), 201


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    identity = str(data.get("identity", "")).strip()
    password = str(data.get("password", ""))
    with database() as db:
        user = db.execute("SELECT * FROM users WHERE email = ? COLLATE NOCASE OR phone = ?", (identity, identity)).fetchone()
    if not user:
        return json_error("Email, phone number, or password is incorrect.", 401)
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(user["password_salt"]), 310_000).hex()
    if not hmac.compare_digest(candidate, user["password_hash"]):
        return json_error("Email, phone number, or password is incorrect.", 401)
    session.clear()
    session["user_id"] = user["id"]
    session["user_name"] = user["full_name"]
    return jsonify({"message": "You are signed in.", "name": user["full_name"]})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "You are signed out."})


@app.get("/api/reports")
def list_reports():
    with database() as db:
        rows = db.execute("SELECT id,kind,title,category,report_date AS date,location,description AS text FROM reports WHERE status='published' ORDER BY id DESC LIMIT 100").fetchall()
    return jsonify([dict(row) for row in rows])


@app.post("/api/reports")
def create_report():
    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind", "")).strip().lower()
    title = str(data.get("title", "")).strip()
    category = str(data.get("category", "")).strip()
    location = str(data.get("location", "")).strip()
    description = str(data.get("description", "")).strip()
    report_date = str(data.get("date", "")).strip()
    if kind not in {"lost", "found", "missing"}:
        return json_error("Choose lost, found, or missing person report type.")
    if not all((title, category, location, description, report_date)):
        return json_error("Complete all required report fields.")
    try:
        date.fromisoformat(report_date)
    except ValueError:
        return json_error("Enter a valid report date.")
    status = "pending_review" if kind == "missing" else "published"
    with database() as db:
        cur = db.execute("INSERT INTO reports(kind,title,category,report_date,location,description,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                         (kind, title, category, report_date, location, description, status, now_iso()))
        report_id = cur.lastrowid
    return jsonify({"id": report_id, "status": status, "message": "Saved to the local database."}), 201


@app.post("/api/volunteer-signups")
def volunteer_signup():
    data = request.get_json(silent=True) or {}
    activity = str(data.get("activity", "")).strip()
    full_name = str(data.get("name", "")).strip()
    contact = str(data.get("contact", "")).strip()
    note = str(data.get("note", "")).strip()
    if not all((activity, full_name, contact)):
        return json_error("Activity, name, and contact are required.")
    with database() as db:
        cur = db.execute("INSERT INTO volunteer_signups(activity,full_name,contact,note,created_at) VALUES(?,?,?,?,?)",
                         (activity, full_name, contact, note, now_iso()))
    return jsonify({"id": cur.lastrowid, "message": "Your interest was saved locally."}), 201


init_db()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
