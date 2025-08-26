from flask import Blueprint, request, jsonify
from models import db, Project, Coder, Result, ProjectFile
from datetime import datetime
import json
import os
import csv

coding_bp = Blueprint('coding', __name__)

def load_video_list(project):
    folder = os.path.join("uploads", project.slug)
    videos = []
    seen = set()
    if os.path.isdir(folder):
        for f in os.listdir(folder):
            path = os.path.join(folder, f)
            if path.endswith(".csv"):
                with open(path, newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        vid = row.get("id") or row.get("video_id")
                        if vid and vid not in seen:
                            videos.append(row)
                            seen.add(vid)
    return videos

def extract_metadata(row):
    return {
        "author": row.get("author_name") or row.get("author_nickName"),
        "description": row.get("text"),
        "create_time": row.get("createTime"),
        "view_count": safe_int(row.get("playCount")),
        "like_count": safe_int(row.get("diggCount")),
        "share_count": safe_int(row.get("shareCount")),
        "comment_count": safe_int(row.get("commentCount")),
        "save_count": safe_int(row.get("collectCount"))
    }

def safe_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        return 0

@coding_bp.route("/api/video-at-index")
def video_at_index():
    slug = request.args.get("project")
    coder_name = request.args.get("coder")
    index_param = request.args.get("index")

    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first() if coder_name else None
    if not coder and coder_name:
        return jsonify({"error": "Coder not found"}), 404

    videos = load_video_list(project)
    total_videos = len(videos)

    if index_param is not None:
        try:
            index = int(index_param)
        except ValueError:
            return jsonify({"error": "Invalid index"}), 400
    elif coder:
        index = coder.progress_index
    else:
        index = 0  # fallback if coder is not provided

    if index < 0 or index >= total_videos:
        return jsonify({"error": "Index out of range"}), 400

    row = videos[index]
    video_id = row.get("id") or row.get("video_id")

    # Fetch existing response if present
    response_data = {}
    if coder:
        result = Result.query.filter_by(
            project_id=project.id,
            coder_id=coder.id,
            video_id=video_id
        ).first()
        response_data = {
            "categories": json.loads(result.categories) if result and result.categories else {},
            "notes": result.notes if result else ""
        }

    return jsonify({
        "id": video_id,
        "metadata": extract_metadata(row),
        "response": response_data,
        "index": index,
        "total": total_videos
    })


@coding_bp.route("/api/save-progress", methods=["POST"])
def save_progress():
    data = request.get_json()
    slug = data.get("project")
    coder_name = data.get("coder")
    video_id = data.get("video_id")
    response = data.get("response")  # includes categories + notes

    if not slug or not coder_name or not video_id or not response:
        return jsonify({"error": "Missing required fields"}), 400

    excluded = response.get("excluded", False)
    categories = response.get("categories") or {
        k: v for k, v in response.items() if k != "notes" and k != "excluded"
    }
    notes = response.get("notes", "")

    project = Project.query.filter_by(slug=slug).first()
    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not project or not coder:
        return jsonify({"error": "Project or Coder not found"}), 404

    result = Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).first()

    if not result:
        result = Result(
            project_id=project.id,
            coder_id=coder.id,
            video_id=video_id,
            categories=json.dumps(categories) if not excluded else json.dumps({}),
            notes=notes,
            status="draft",
            excluded=excluded,
            timestamp=datetime.utcnow()
        )
        db.session.add(result)
    else:
        result.categories = json.dumps(categories) if not excluded else json.dumps({})
        result.notes = notes
        result.excluded = excluded
        result.timestamp = datetime.utcnow()
        result.status = "draft"

    db.session.commit()
    return jsonify({"success": True})

@coding_bp.route("/api/submit", methods=["POST"])
def submit():
    data = request.get_json()
    slug = data.get("project")
    coder_name = data.get("coder")
    video_id = data.get("video_id")
    categories = data.get("categories")
    notes = data.get("notes", "")
    excluded = data.get("excluded", False)

    if not slug or not coder_name or not video_id:
        return jsonify({"error": "Missing required fields"}), 400
    
    # For excluded videos, categories is not required
    if not excluded and not categories:
        return jsonify({"error": "Missing categories for non-excluded video"}), 400

    project = Project.query.filter_by(slug=slug).first()
    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not project or not coder:
        return jsonify({"error": "Project or Coder not found"}), 404

    Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).delete()

    result = Result(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id,
        categories=json.dumps(categories) if not excluded else json.dumps({}),
        notes=notes,
        status="submitted",
        excluded=excluded,
        timestamp=datetime.utcnow()
    )
    db.session.add(result)

    coder.progress_index += 1
    db.session.commit()

    return jsonify({"success": True})

@coding_bp.route("/api/codebook", methods=["POST"])
def update_codebook():
    data = request.get_json()
    slug = data.get("project")
    category = data.get("category")
    tag = data.get("tag")

    if not slug or not category:
        return jsonify({"error": "Missing category or project"}), 400

    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    try:
        codebook = json.loads(project.codebook or "[]")
    except:
        codebook = []

    existing = next((c for c in codebook if c.get("category") == category), None)

    if not existing:
        new_entry = {"category": category, "tags": [tag] if tag else []}
        codebook.append(new_entry)
    else:
        if tag and tag not in existing["tags"]:
            existing["tags"].append(tag)

    project.codebook = json.dumps(codebook)
    db.session.commit()

    return jsonify({"success": True})