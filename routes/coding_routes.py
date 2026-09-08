from flask import Blueprint, request, jsonify
from models import db, Project, Coder, Result, ProjectFile
from datetime import datetime
import json
import os
import csv

coding_bp = Blueprint('coding', __name__)

UPLOAD_ROOT = os.environ.get(
    "UPLOAD_ROOT",
    "/var/www/qual-coder/qual-coding-backend/uploads"
)

def load_video_list(project):
    folder = os.path.join(UPLOAD_ROOT, project.slug)
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
    # Convert Unix timestamp to human-readable format
    create_time_raw = row.get("createTime")
    create_time = None
    if create_time_raw:
        try:
            # Convert Unix timestamp to readable date
            from datetime import datetime
            timestamp = int(create_time_raw)
            create_time = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            create_time = create_time_raw  # Fallback to original value
    
    return {
        "author": row.get("author_name") or row.get("author_nickName"),
        "description": row.get("text"),
        "create_time": create_time,
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

@coding_bp.route("/video-at-index")
def video_at_index():
    slug = request.args.get("project")
    coder_name = request.args.get("coder")
    index_param = request.args.get("index")
    filter_type = request.args.get("filter", "all")

    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first() if coder_name else None
    if not coder and coder_name:
        return jsonify({"error": "Coder not found"}), 404

    videos = load_video_list(project)
    
    # Apply filtering based on coder's progress
    print(f"DEBUG: filter_type={filter_type}, coder={coder}, coder_name={coder_name}")
    if filter_type != "all":
        filtered_videos = []
        for i, video in enumerate(videos):
            video_id = video.get("id") or video.get("video_id")
            result = None
            if coder:
                result = Result.query.filter_by(
                    project_id=project.id,
                    coder_id=coder.id,
                    video_id=video_id
                ).first()
            
            if filter_type == "uncoded" and not result:
                filtered_videos.append((i, video))
            elif filter_type == "saved" and result and result.status == "draft":
                filtered_videos.append((i, video))
            elif filter_type == "submitted" and result and result.status == "submitted":
                filtered_videos.append((i, video))
            elif filter_type == "excluded" and result and result.excluded:
                filtered_videos.append((i, video))
        
        # Return filtered video list with original indices
        processed_videos = []
        for orig_idx, video in filtered_videos:
            video_id = video.get("id") or video.get("video_id")
            processed_video = {
                "id": video_id,
                "metadata": extract_metadata(video),
                "index": orig_idx
            }
            processed_videos.append({"original_index": orig_idx, "video": processed_video})
        
        return jsonify({
            "filtered_videos": processed_videos,
            "total": len(filtered_videos)
        })
    
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
            "notes": result.notes if result else "",
            "status": result.status if result else "draft",
            "excluded": result.excluded if result else False
        }

    return jsonify({
        "id": video_id,
        "metadata": extract_metadata(row),
        "response": response_data,
        "index": index,
        "total": total_videos
    })


@coding_bp.route("/save-progress", methods=["POST"])
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
        # Preserve submitted status - autosave should not revert submitted work back to draft
        # Only update status to draft if it's not already submitted
        if result.status != "submitted":
            result.status = "draft"
        result.categories = json.dumps(categories) if not excluded else json.dumps({})
        result.notes = notes
        result.excluded = excluded
        result.timestamp = datetime.utcnow()

    db.session.commit()
    # Return the final status so frontend can track it
    return jsonify({
        "success": True,
        "status": result.status
    })

@coding_bp.route("/submit", methods=["POST"])
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
    # Require at least one tag selected for non-excluded videos (reject e.g. {"Style": [], "Color": []})
    if not excluded and not any(tags for tags in (categories or {}).values()):
        return jsonify({"error": "At least one tag must be selected, or the video must be marked as excluded."}), 400

    project = Project.query.filter_by(slug=slug).first()
    coder = Coder.query.filter_by(name=coder_name, project_id=project.id).first()
    if not project or not coder:
        return jsonify({"error": "Project or Coder not found"}), 404

    # Update existing record instead of delete+create to avoid race conditions
    result = Result.query.filter_by(
        project_id=project.id,
        coder_id=coder.id,
        video_id=video_id
    ).first()

    if not result:
        # Create new record if it doesn't exist
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
    else:
        # Update existing record - set status to submitted
        result.categories = json.dumps(categories) if not excluded else json.dumps({})
        result.notes = notes
        result.status = "submitted"
        result.excluded = excluded
        result.timestamp = datetime.utcnow()

    coder.progress_index += 1
    db.session.commit()

    # Return status so frontend can immediately update state
    return jsonify({
        "success": True,
        "status": result.status
    })

@coding_bp.route("/codebook", methods=["POST"])
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
        new_entry = {"category": category, "tags": [{"tag": tag, "description": ""}] if tag else []}
        codebook.append(new_entry)
    else:
        if tag and not any(t.get("tag") == tag for t in existing["tags"] if isinstance(t, dict)):
            existing["tags"].append({"tag": tag, "description": ""})

    project.codebook = json.dumps(codebook)
    db.session.commit()

    return jsonify({"success": True})
