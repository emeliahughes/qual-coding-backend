from flask import Blueprint, request, jsonify
from models import db, Project, Coder, Result
from datetime import datetime
import json

coding_bp = Blueprint('coding', __name__)

@coding_bp.route("/api/next-video", methods=["GET"])
def next_video():
    project_slug = request.args.get("project")
    coder_name = request.args.get("coder")

    if not project_slug or not coder_name:
        return jsonify({"error": "Missing project or coder name"}), 400

    project = Project.query.filter_by(slug=project_slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not coder:
        return jsonify({"error": "Coder not found"}), 404

    csv_data, error = load_project_csv(project)
    if error:
        return jsonify({"error": error}), 500

    if coder.progress_index >= len(csv_data):
        return jsonify({"done": True})  # Reached end

    video = csv_data[coder.progress_index]
    video_id = video.get("video_id")

    # Check for any saved progress (draft or submitted)
    saved = Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).first()

    progress = {
        "categories": json.loads(saved.categories) if saved and saved.categories else {},
        "notes": saved.notes if saved else "",
        "status": saved.status if saved else "new"
    }

    return jsonify({
        "index": coder.progress_index,
        "video": video,
        "savedProgress": progress
    })

@coding_bp.route("/api/previous-video", methods=["GET"])
def previous_video():
    project_slug = request.args.get("project")
    coder_name = request.args.get("coder")

    if not project_slug or not coder_name:
        return jsonify({"error": "Missing project or coder name"}), 400

    project = Project.query.filter_by(slug=project_slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not coder:
        return jsonify({"error": "Coder not found"}), 404

    csv_data, error = load_project_csv(project)
    if error:
        return jsonify({"error": error}), 500

    # Clamp index to >= 0
    previous_index = max(coder.progress_index - 1, 0)
    video = csv_data[previous_index]
    video_id = video.get("video_id")

    # Load any existing saved progress
    saved = Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).first()

    progress = {
        "categories": json.loads(saved.categories) if saved and saved.categories else {},
        "notes": saved.notes if saved else "",
        "status": saved.status if saved else "new"
    }

    return jsonify({
        "index": previous_index,
        "video": video,
        "savedProgress": progress
    })

@coding_bp.route("/api/video-at-index", methods=["GET"])
def video_at_index():
    project_slug = request.args.get("project")
    coder_name = request.args.get("coder")
    index = request.args.get("index")

    if not project_slug or not coder_name or index is None:
        return jsonify({"error": "Missing project, coder, or index"}), 400

    try:
        index = int(index)
    except ValueError:
        return jsonify({"error": "Index must be an integer"}), 400

    project = Project.query.filter_by(slug=project_slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not coder:
        return jsonify({"error": "Coder not found"}), 404

    csv_data, error = load_project_csv(project)
    if error:
        return jsonify({"error": error}), 500

    if index < 0 or index >= len(csv_data):
        return jsonify({"error": "Index out of bounds"}), 400

    video = csv_data[index]
    video_id = video.get("video_id")

    # Load any saved result (draft or submitted)
    saved = Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).first()

    progress = {
        "categories": json.loads(saved.categories) if saved and saved.categories else {},
        "notes": saved.notes if saved else "",
        "status": saved.status if saved else "new"
    }

    return jsonify({
        "index": index,
        "video": video,
        "savedProgress": progress
    })


@coding_bp.route("/api/submit", methods=["POST"])
def submit():
    data = request.get_json()
    slug = data.get("project")
    coder_name = data.get("coder")
    video_id = data.get("video_id")
    categories = data.get("categories")
    notes = data.get("notes", "")

    if not slug or not coder_name or not video_id or not categories:
        return jsonify({"error": "Missing required fields"}), 400

    # Lookup project and coder
    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not coder:
        return jsonify({"error": "Coder not found"}), 404

    # Remove existing result, if any
    Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).delete()

    # Insert new result
    result = Result(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id,
        categories=json.dumps(categories),
        notes=notes,
        status="submitted",
        timestamp=datetime.utcnow()
    )
    db.session.add(result)

    # Advance coder progress
    coder.progress_index += 1
    db.session.commit()

    return jsonify({"success": True})


@coding_bp.route("/api/save-progress", methods=["POST"])
def save_progress():
    data = request.get_json()
    slug = data.get("project")
    coder_name = data.get("coder")
    video_id = data.get("video_id")
    categories = data.get("categories")
    notes = data.get("notes", "")

    if not slug or not coder_name or not video_id:
        return jsonify({"error": "Missing required fields"}), 400

    # Lookup project and coder
    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not coder:
        return jsonify({"error": "Coder not found"}), 404

    # Always overwrite or create
    result = Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).first()

    if result:
        result.categories = json.dumps(categories)
        result.notes = notes
        result.status = "draft"
        result.timestamp = datetime.utcnow()
    else:
        result = Result(
            project_id=project.id,
            coder_id=coder.id,
            video_id=video_id,
            categories=json.dumps(categories),
            notes=notes,
            status="draft",
            timestamp=datetime.utcnow()
        )
        db.session.add(result)

    db.session.commit()
    return jsonify({"success": True})
