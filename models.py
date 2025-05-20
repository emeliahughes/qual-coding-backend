from app import db
from datetime import datetime

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String, unique=True, nullable=False)
    title = db.Column(db.String, nullable=False)
    data_file = db.Column(db.String)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    coders = db.relationship("Coder", backref="project", lazy=True)
    results = db.relationship("Result", backref="project", lazy=True)

class Coder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    progress_index = db.Column(db.Integer, default=0)  # NEW
    results = db.relationship("Result", backref="coder", lazy=True)


class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    coder_id = db.Column(db.Integer, db.ForeignKey('coder.id'), nullable=False)
    video_id = db.Column(db.String, nullable=False)
    categories = db.Column(db.Text)  # JSON string
    notes = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String, default="draft")
