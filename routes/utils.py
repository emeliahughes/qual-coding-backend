from flask import jsonify, Response
from models import db, Project, Result, Coder
import json
import csv
import io

def generate_codebook_json(slug):
    project = Project.query.filter_by(slug=slug).first()
    if not project or not project.codebook:
        return jsonify({"error": "No codebook found"}), 404

    codebook_data = json.loads(project.codebook or "[]")
    json_str = json.dumps(codebook_data, indent=2)

    return Response(
        json_str,
        mimetype='application/json',
        headers={
            "Content-Disposition": f"attachment;filename={slug}_codebook.json"
        }
    )

def generate_results_csv(slug):
    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return jsonify({"error": "Project not found"}), 404

    results = Result.query.filter_by(project_id=project.id).all()
    if not results:
        return jsonify({"error": "No results found"}), 404

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV headers
    writer.writerow(["coder", "video_id", "status", "timestamp", "notes", "categories"])
    
    for r in results:
        # Determine the actual status
        if r.excluded:
            actual_status = "excluded"
        elif r.status == "submitted":
            actual_status = "submitted"
        else:
            actual_status = "saved"  # draft status
        
        # Parse categories for better readability
        categories_display = ""
        if r.categories and not r.excluded:
            try:
                categories_data = json.loads(r.categories)
                category_pairs = []
                for category, tags in categories_data.items():
                    if tags:
                        category_pairs.append(f"{category}: {', '.join(tags)}")
                categories_display = "; ".join(category_pairs)
            except json.JSONDecodeError:
                categories_display = r.categories
        
        writer.writerow([
            r.coder.name,
            r.video_id,
            actual_status,
            r.timestamp.isoformat() if r.timestamp else "",
            r.notes or "",
            categories_display
        ])

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={
            "Content-Disposition": f"attachment;filename={slug}_results.csv"
        }
    )

def get_results_csv_text(slug):
    """Get results CSV as text for the Results page"""
    project = Project.query.filter_by(slug=slug).first()
    if not project:
        return None

    results = Result.query.filter_by(project_id=project.id).all()
    if not results:
        return None

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write CSV headers
    writer.writerow(["coder", "video_id", "status", "timestamp", "notes", "categories"])
    
    for r in results:
        # Determine the actual status
        if r.excluded:
            actual_status = "excluded"
        elif r.status == "submitted":
            actual_status = "submitted"
        else:
            actual_status = "saved"  # draft status
        
        # Parse categories for better readability
        categories_display = ""
        if r.categories and not r.excluded:
            try:
                categories_data = json.loads(r.categories)
                category_pairs = []
                for category, tags in categories_data.items():
                    if tags:
                        category_pairs.append(f"{category}: {', '.join(tags)}")
                categories_display = "; ".join(category_pairs)
            except json.JSONDecodeError:
                categories_display = r.categories
        
        writer.writerow([
            r.coder.name,
            r.video_id,
            actual_status,
            r.timestamp.isoformat() if r.timestamp else "",
            r.notes or "",
            categories_display
        ])

    output.seek(0)
    return output.getvalue()

# Optional placeholder
def load_project_csv(filepath):
    pass
