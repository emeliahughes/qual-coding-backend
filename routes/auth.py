import re
import secrets
from functools import wraps

from flask import g, jsonify, session

from models import ProjectMembership, User, db


USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,79}$")


def normalize_username(value):
    return (value or "").strip().lower()


def current_user():
    if hasattr(g, "current_user"):
        return g.current_user
    user_id = session.get("user_id")
    user = db.session.get(User, user_id) if user_id else None
    if user and not user.is_active:
        session.clear()
        user = None
    g.current_user = user
    return user


def require_authenticated():
    if not current_user():
        return jsonify({"error": "Authentication required"}), 401
    return None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        error = require_authenticated()
        if error:
            return error
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            return jsonify({"error": "Authentication required"}), 401
        if not user.is_admin:
            return jsonify({"error": "Administrator access required"}), 403
        return view(*args, **kwargs)
    return wrapped


def membership_for(user, project):
    if not user or not project:
        return None
    return ProjectMembership.query.filter_by(
        user_id=user.id,
        project_id=project.id,
    ).first()


def can_access_project(user, project):
    return bool(user and project and (user.is_admin or membership_for(user, project)))


def can_manage_project(user, project):
    if not user or not project:
        return False
    if user.is_admin:
        return True
    membership = membership_for(user, project)
    return bool(membership and membership.role == "project_admin")


def can_code_as(user, project, coder):
    if not user or not project or not coder:
        return False
    if user.is_admin:
        return True
    membership = membership_for(user, project)
    if not membership:
        return False
    if membership.role == "project_admin":
        return True
    return membership.coder_id == coder.id


def issue_csrf_token():
    token = secrets.token_urlsafe(32)
    session["csrf_token"] = token
    return token


def serialize_membership(membership):
    return {
        "project_slug": membership.project.slug,
        "project_name": membership.project.name,
        "role": membership.role,
        "coder_name": membership.coder.name if membership.coder else None,
    }


def serialize_user(user, include_memberships=True):
    payload = {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "is_admin": user.is_admin,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
    }
    if include_memberships:
        payload["project_access"] = [
            serialize_membership(membership)
            for membership in sorted(
                user.memberships,
                key=lambda item: item.project.name.lower(),
            )
        ]
    return payload


def validate_username(username):
    return bool(USERNAME_PATTERN.fullmatch(normalize_username(username)))
