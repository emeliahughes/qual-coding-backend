from flask import Blueprint, request, jsonify, send_file
from models import db, Project, Coder, Result, ProjectFile
from sqlalchemy.exc import IntegrityError
from routes.utils import generate_codebook_json, generate_results_csv
from werkzeug.utils import secure_filename
import os, json, csv

project_bp = Blueprint('project', __name__)

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

def refresh_video_count(project):
    videos = load_video_list(project)
    project.video_count = len(videos)
    db.session.commit()
    return videos

@project_bp.route("/api/projects", methods=["POST"])
def create_project():
    data = request.get_json()
    name = data.get("name")
    codebook = data.get("codebook", [])
    coders = data.get("coders", [])

    if not name:
        return jsonify({"error": "Missing project name"}), 400

    slug = name.lower().replace(" ", "-")
    existing = Project.query.filter_by(slug=slug).first()
    if existing:
        return jsonify({"error": "Project already exists"}), 409

    project = Project(name=name, slug=slug, codebook=json.dumps(codebook))
    db.session.add(project)
    db.session.commit()

    for coder in coders:
        db.session.add(Coder(name=coder, project_id=project.id))

    db.session.commit()
    return jsonify({"success": True, "slug": project.slug})

@project_bp.route("/api/projects", methods=["GET"])
def list_projects():
    projects = Project.query.all()
    result = []
    for p in projects:
        refresh_video_count(p)  # ✅ sync DB, discard return value
        coders = [c.name for c in p.coders]
        responses = {}
        for c in p.coders:
            responses[c.name] = []
            for r in c.results:
                # Include both draft and submitted responses for progress tracking
                if r.excluded:
                    responses[c.name].append({"video_id": r.video_id, "excluded": True})
                else:
                    responses[c.name].append({
                        "video_id": r.video_id, 
                        "status": r.status,
                        "excluded": False
                    })
        file_names = [f.filename for f in p.project_files]
        result.append({
            "name": p.name,
            "slug": p.slug,
            "coders": coders,
            "video_count": p.video_count,  # ✅ just the number
            "responses": responses,
            "project_files": file_names
        })
    return jsonify(result)


def update_results_for_codebook_changes(project, old_codebook, new_codebook):
    """Update all existing results when codebook changes to maintain data integrity"""
    try:
        old_codebook_data = json.loads(old_codebook) if old_codebook else []
        new_codebook_data = json.loads(new_codebook) if new_codebook else []
        
        # Create mapping from old to new category/tag names
        category_mapping = {}
        tag_mapping = {}
        
        # Build mappings for renamed categories and tags
        for old_cat in old_codebook_data:
            old_cat_name = old_cat.get("category", "")
            old_tags = old_cat.get("tags", [])
            
            # Find corresponding new category
            for new_cat in new_codebook_data:
                new_cat_name = new_cat.get("category", "")
                new_tags = new_cat.get("tags", [])
                
                # Check if this might be the same category (exact match or similar)
                if old_cat_name == new_cat_name:
                    category_mapping[old_cat_name] = new_cat_name
                    
                    # Map old tags to new tags
                    for i, old_tag in enumerate(old_tags):
                        old_tag_name = old_tag if isinstance(old_tag, str) else old_tag.get("tag", "")
                        if i < len(new_tags):
                            new_tag = new_tags[i]
                            new_tag_name = new_tag if isinstance(new_tag, str) else new_tag.get("tag", "")
                            tag_mapping[f"{old_cat_name}:{old_tag_name}"] = f"{new_cat_name}:{new_tag_name}"
                    break
        
        # Update all results for this project
        results = Result.query.filter_by(project_id=project.id).all()
        updated_count = 0
        
        for result in results:
            if result.categories:
                try:
                    categories_data = json.loads(result.categories)
                    updated_categories = {}
                    needs_update = False
                    
                    for old_cat_name, tags in categories_data.items():
                        new_cat_name = category_mapping.get(old_cat_name, old_cat_name)
                        
                        if new_cat_name in new_codebook_data:
                            # Category still exists, update tags
                            updated_tags = []
                            for tag in tags:
                                old_tag_key = f"{old_cat_name}:{tag}"
                                new_tag_key = tag_mapping.get(old_tag_key, f"{new_cat_name}:{tag}")
                                new_tag = new_tag_key.split(":", 1)[1] if ":" in new_tag_key else tag
                                updated_tags.append(new_tag)
                            
                            updated_categories[new_cat_name] = updated_tags
                            if old_cat_name != new_cat_name or any(old_tag != new_tag for old_tag, new_tag in zip(tags, updated_tags)):
                                needs_update = True
                        else:
                            # Category was deleted, remove it
                            needs_update = True
                    
                    if needs_update:
                        result.categories = json.dumps(updated_categories)
                        updated_count += 1
                        
                except json.JSONDecodeError:
                    continue
        
        db.session.commit()
        return updated_count
        
    except Exception as e:
        print(f"Error updating results for codebook changes: {e}")
        return 0

@project_bp.route("/api/project/<slug>", methods=["PUT"])
def update_project(slug):
    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    data = request.get_json()
    old_codebook = project.codebook
    project.name = data.get("name", project.name)
    new_codebook = data.get("codebook", [])
    project.codebook = json.dumps(new_codebook)
    
    # Update existing results to maintain data integrity
    updated_count = update_results_for_codebook_changes(project, old_codebook, project.codebook)
    
    db.session.commit()
    return jsonify({"success": True, "updated_results": updated_count})

@project_bp.route("/api/project/<slug>", methods=["DELETE"])
def delete_project(slug):
    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    db.session.delete(project)
    db.session.commit()
    return jsonify({"success": True})

@project_bp.route("/api/project-info", methods=["GET"])
def project_info():
    slug = request.args.get("project")
    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Not found"}), 404
    coders = [c.name for c in project.coders]
    return jsonify({
        "name": project.name,
        "slug": slug,
        "coders": coders,
        "codebook": json.loads(project.codebook or "[]")
    })


@project_bp.route("/api/upload-data", methods=["POST"])
def upload_data():
    file = request.files.get("file")
    slug = request.form.get("project")
    if not file or not slug:
        return jsonify({"error": "Missing file or project"}), 400

    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    upload_folder = os.path.join("uploads", slug)
    os.makedirs(upload_folder, exist_ok=True)

    original_filename = secure_filename(file.filename)
    base_filename = project.name.replace(" ", "_")
    ext = os.path.splitext(original_filename)[1] or ".csv"
    i = 1
    new_filename = f"{base_filename}{ext}"
    filepath = os.path.join(upload_folder, new_filename)
    while os.path.exists(filepath):
        new_filename = f"{base_filename}_{i}{ext}"
        filepath = os.path.join(upload_folder, new_filename)
        i += 1

    file.save(filepath)

    # Save metadata about the uploaded file
    pf = ProjectFile(project_id=project.id, filename=new_filename, original_name=original_filename)
    db.session.add(pf)
    db.session.commit()

    # ✅ Recalculate and store accurate video count
    refresh_video_count(project)

    return jsonify({"success": True, "filename": new_filename})

@project_bp.route("/api/download-codebook", methods=["GET"])
def download_codebook():
    slug = request.args.get("project")
    return generate_codebook_json(slug)

@project_bp.route("/api/download-results", methods=["GET"])
def download_results():
    slug = request.args.get("project")
    return generate_results_csv(slug)

@project_bp.route("/api/coder", methods=["POST"])
def add_coder():
    data = request.get_json()
    project = Project.query.filter_by(slug=data.get("project")).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404
    new = Coder(name=data["coder"], project_id=project.id)
    db.session.add(new)
    db.session.commit()
    return jsonify({"success": True})

@project_bp.route("/api/coder", methods=["PUT"])
def rename_coder():
    data = request.get_json()
    project = Project.query.filter_by(slug=data.get("project")).first()
    coder = Coder.query.filter_by(name=data.get("old_name"), project_id=project.id).first()
    if not coder:
        return jsonify({"error": "Coder not found"}), 404
    coder.name = data["new_name"]
    db.session.commit()
    return jsonify({"success": True})

@project_bp.route("/api/coder", methods=["DELETE"])
def delete_coder():
    data = request.get_json()
    project = Project.query.filter_by(slug=data.get("project")).first()
    coder = Coder.query.filter_by(name=data.get("coder"), project_id=project.id).first()
    db.session.delete(coder)
    db.session.commit()
    return jsonify({"success": True})
