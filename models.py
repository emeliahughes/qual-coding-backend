from app import db
from datetime import datetime

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, nullable=False)
    codebook = db.Column(db.Text)
    video_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    coders = db.relationship("Coder", backref="project", lazy=True)
    results = db.relationship("Result", backref="project", lazy=True)
    project_files = db.relationship("ProjectFile", backref="project", lazy=True)

class ProjectFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    filename = db.Column(db.String, nullable=False)            # internal filename (renamed)
    original_name = db.Column(db.String, nullable=False)       # original uploaded name
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Coder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    progress_index = db.Column(db.Integer, default=0)
    results = db.relationship("Result", backref="coder", lazy=True)

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    coder_id = db.Column(db.Integer, db.ForeignKey('coder.id'), nullable=False)
    video_id = db.Column(db.String, nullable=False)
    categories = db.Column(db.Text)
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String, default="draft")
    excluded = db.Column(db.Boolean, default=False)
