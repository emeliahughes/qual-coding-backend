from flask import Flask, jsonify, request, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
import os
import secrets
from datetime import timedelta

app = Flask(__name__)


def load_or_create_secret_key():
    configured = os.environ.get("SECRET_KEY")
    if configured:
        return configured

    data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)), "data")
    os.makedirs(data_dir, exist_ok=True)
    secret_path = os.path.join(data_dir, ".session_secret")
    try:
        with open(secret_path, "r", encoding="utf-8") as secret_file:
            existing = secret_file.read().strip()
            if existing:
                return existing
    except FileNotFoundError:
        pass

    generated = secrets.token_urlsafe(48)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        descriptor = os.open(secret_path, flags, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as secret_file:
            secret_file.write(generated)
        return generated
    except FileExistsError:
        with open(secret_path, "r", encoding="utf-8") as secret_file:
            return secret_file.read().strip()


app.config.update(
    SECRET_KEY=load_or_create_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true",
    PERMANENT_SESSION_LIFETIME=timedelta(hours=int(os.environ.get("SESSION_HOURS", "12"))),
)

allowed_origins = [
    origin.strip()
    for origin in os.environ.get("APP_ORIGINS", "https://qual-coder.com").split(",")
    if origin.strip()
]
CORS(app, origins=allowed_origins, supports_credentials=True)

# Database config
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    'sqlite:///' + os.path.join(basedir, 'data', 'database.db')
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# DB setup
db = SQLAlchemy()
db.init_app(app)

# Register route blueprints
from routes.project_routes import project_bp
from routes.coding_routes import coding_bp
from routes.auth_routes import auth_bp

app.register_blueprint(auth_bp)
app.register_blueprint(project_bp)
app.register_blueprint(coding_bp)


@app.before_request
def verify_csrf_token():
    if session.get("user_id"):
        from routes.auth import current_user
        user = current_user()
        password_change_endpoints = {
            "auth.me",
            "auth.change_password",
            "auth.logout",
        }
        if user and user.must_change_password and request.endpoint not in password_change_endpoints:
            return jsonify({"error": "Password change required"}), 403

    if request.method in {"GET", "HEAD", "OPTIONS"} or request.endpoint == "auth.login":
        return None
    if not session.get("user_id"):
        return None
    expected = session.get("csrf_token")
    provided = request.headers.get("X-CSRF-Token")
    if not expected or not provided or not secrets.compare_digest(expected, provided):
        return jsonify({"error": "Invalid or missing CSRF token"}), 403
    return None


@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response

if __name__ == "__main__":
    app.run(debug=True)
