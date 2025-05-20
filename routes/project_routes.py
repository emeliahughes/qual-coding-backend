from flask import Blueprint, request, jsonify
from models import db, Project, Coder
from sqlalchemy.exc import IntegrityError

project_bp = Blueprint('project', __name__)

@project_bp.route("/api/projects", methods=["POST"])
def create_project():
    data = request.get_json()
    slug = data.get("slug")
    title = data.get("title")
    data_file = data.get("data_file")
    coders = data.get("coders", [])

    if not slug or not title or not data_file:
        return jsonify({"error": "Missing required fields"}), 400

    try:
        project = Project(slug=slug, title=title, data_file=data_file)
        db.session.add(project)
        db.session.commit()

        for coder_name in coders:
            coder = Coder(name=coder_name, project_id=project.id)
            db.session.add(coder)

        db.session.commit()
        return jsonify({"success": True, "project_id": project.id})
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Project with that slug already exists"}), 409
