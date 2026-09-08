from flask import Blueprint, jsonify, request, session

from models import Coder, Project, ProjectMembership, User, db
from routes.auth import (
    admin_required,
    current_user,
    issue_csrf_token,
    login_required,
    normalize_username,
    serialize_user,
    validate_username,
)


auth_bp = Blueprint("auth", __name__)


def validate_password(password):
    return isinstance(password, str) and len(password) >= 12


def sync_project_access(user, access_entries):
    requested = access_entries or []
    normalized = []
    seen_projects = set()

    for entry in requested:
        slug = (entry.get("project_slug") or "").strip()
        role = entry.get("role", "researcher")
        coder_name = (entry.get("coder_name") or "").strip() or None
        if not slug or slug in seen_projects:
            raise ValueError("Each project may be assigned only once")
        if role not in {"researcher", "project_admin"}:
            raise ValueError("Invalid project role")

        project = Project.query.filter_by(slug=slug).first()
        if not project:
            raise ValueError(f"Unknown project: {slug}")
        coder = None
        if coder_name:
            coder = Coder.query.filter_by(project_id=project.id, name=coder_name).first()
            if not coder:
                raise ValueError(f"Unknown coder for {project.name}: {coder_name}")
        if role == "researcher" and not coder:
            raise ValueError(f"A coder identity is required for researcher access to {project.name}")

        normalized.append((project, coder, role))
        seen_projects.add(slug)

    ProjectMembership.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    for project, coder, role in normalized:
        db.session.add(ProjectMembership(
            user_id=user.id,
            project_id=project.id,
            coder_id=coder.id if coder else None,
            role=role,
        ))


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = normalize_username(data.get("username"))
    password = data.get("password") or ""
    user = User.query.filter_by(username=username).first()
    if not user or not user.is_active or not user.check_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    session.clear()
    session.permanent = True
    session["user_id"] = user.id
    csrf_token = issue_csrf_token()
    return jsonify({"user": serialize_user(user), "csrf_token": csrf_token})


@auth_bp.route("/auth/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"success": True})


@auth_bp.route("/auth/me", methods=["GET"])
@login_required
def me():
    token = session.get("csrf_token") or issue_csrf_token()
    return jsonify({"user": serialize_user(current_user()), "csrf_token": token})


@auth_bp.route("/auth/change-password", methods=["POST"])
@login_required
def change_password():
    data = request.get_json(silent=True) or {}
    user = current_user()
    if not user.check_password(data.get("current_password") or ""):
        return jsonify({"error": "Current password is incorrect"}), 400
    new_password = data.get("new_password") or ""
    if not validate_password(new_password):
        return jsonify({"error": "New password must contain at least 12 characters"}), 400
    user.set_password(new_password)
    user.must_change_password = False
    db.session.commit()
    session.clear()
    return jsonify({"success": True, "reauthenticate": True})


@auth_bp.route("/admin/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.order_by(User.display_name, User.username).all()
    projects = Project.query.order_by(Project.name).all()
    return jsonify({
        "users": [serialize_user(user) for user in users],
        "projects": [
            {
                "slug": project.slug,
                "name": project.name,
                "coders": [coder.name for coder in project.coders],
            }
            for project in projects
        ],
    })


@auth_bp.route("/admin/users", methods=["POST"])
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = normalize_username(data.get("username"))
    display_name = (data.get("display_name") or "").strip()
    password = data.get("password") or ""

    if not validate_username(username):
        return jsonify({"error": "Username must be 3-80 lowercase letters, numbers, dots, dashes, or underscores"}), 400
    if not display_name:
        return jsonify({"error": "Display name is required"}), 400
    if not validate_password(password):
        return jsonify({"error": "Password must contain at least 12 characters"}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username already exists"}), 409

    user = User(
        username=username,
        display_name=display_name,
        is_admin=bool(data.get("is_admin", False)),
        is_active=True,
        must_change_password=True,
    )
    user.set_password(password)
    db.session.add(user)
    try:
        db.session.flush()
        sync_project_access(user, data.get("project_access", []))
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 400
    return jsonify({"user": serialize_user(user)}), 201


@auth_bp.route("/admin/users/<int:user_id>", methods=["PUT"])
@admin_required
def update_user(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    data = request.get_json(silent=True) or {}

    username = normalize_username(data.get("username", user.username))
    display_name = (data.get("display_name", user.display_name) or "").strip()
    if not validate_username(username) or not display_name:
        return jsonify({"error": "Valid username and display name are required"}), 400
    duplicate = User.query.filter(User.username == username, User.id != user.id).first()
    if duplicate:
        return jsonify({"error": "Username already exists"}), 409

    requested_admin = bool(data.get("is_admin", user.is_admin))
    requested_active = bool(data.get("is_active", user.is_active))
    if user.is_admin and (not requested_admin or not requested_active):
        active_admins = User.query.filter_by(is_admin=True, is_active=True).count()
        if active_admins <= 1:
            return jsonify({"error": "The final active administrator cannot be removed or deactivated"}), 400

    password = data.get("password")
    if password and not validate_password(password):
        return jsonify({"error": "Password must contain at least 12 characters"}), 400

    user.username = username
    user.display_name = display_name
    user.is_admin = requested_admin
    user.is_active = requested_active
    if password:
        user.set_password(password)
        user.must_change_password = user.id != current_user().id

    try:
        sync_project_access(user, data.get("project_access", []))
        db.session.commit()
    except ValueError as error:
        db.session.rollback()
        return jsonify({"error": str(error)}), 400
    return jsonify({"user": serialize_user(user)})
