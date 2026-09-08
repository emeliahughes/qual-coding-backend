from app import db
from datetime import datetime
from werkzeug.security import check_password_hash, generate_password_hash


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    display_name = db.Column(db.String(160), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    must_change_password = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    memberships = db.relationship(
        "ProjectMembership",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan",
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256:600000")

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    memberships = db.relationship("ProjectMembership", backref="coder", lazy=True)


class ProjectMembership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    coder_id = db.Column(db.Integer, db.ForeignKey('coder.id'), nullable=True)
    role = db.Column(db.String(32), default="researcher", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    project = db.relationship("Project", backref=db.backref("memberships", lazy=True))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'project_id', name='uq_membership_user_project'),
    )

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
