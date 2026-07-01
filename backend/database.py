"""
Database layer.

Defines a single SQLAlchemy instance + three lightweight models that
track uploads, generated reports, and pipeline runs.
"""
from datetime import datetime
# pyrefly: ignore [missing-import]
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Upload(db.Model):
    """One row per uploaded dataset file."""
    __tablename__ = 'uploads'

    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)   # csv / xlsx
    size_bytes = db.Column(db.Integer, nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    reports = db.relationship('Report', backref='upload', lazy=True)
    runs = db.relationship('ProcessRun', backref='upload', lazy=True)

    def to_dict(self):
        return {
            'file_id': self.file_id,
            'filename': self.original_filename,
            'file_type': self.file_type,
            'size': self.size_bytes,
            'uploaded_at': self.uploaded_at.isoformat(),
        }


class Report(db.Model):
    """Generated PDF report metadata."""
    __tablename__ = 'reports'

    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    file_id = db.Column(db.String(64), nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(512), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            'file_id': self.file_id,
            'filename': self.filename,
            'url': f"/reports/{self.filename}",
            'created_at': self.created_at.isoformat(),
        }


class ProcessRun(db.Model):
    """One row per pipeline invocation — useful as an audit/history log."""
    __tablename__ = 'process_runs'

    id = db.Column(db.Integer, primary_key=True)
    upload_id = db.Column(db.Integer, db.ForeignKey('uploads.id'), nullable=False)
    file_id = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False)   # success / error
    message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'file_id': self.file_id,
            'status': self.status,
            'message': self.message,
            'started_at': self.started_at.isoformat(),
            'finished_at': self.finished_at.isoformat() if self.finished_at else None,
        }