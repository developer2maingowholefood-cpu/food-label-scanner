from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import os

# SQLAlchemy instance (to be initialized in app.py)
db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    # User health conditions for personalized ingredient explanations
    health_conditions = db.Column(db.Text, nullable=True)
    # User preference for ingredient checking (kosher, halal, vegetarian, vegan, etc.)
    dietary_preference = db.Column(db.String(50), nullable=True, default='none')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(128), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    scans = db.relationship('Scan', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Scan(db.Model):
    __tablename__ = 'scans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    scan_data = db.Column(db.JSON, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.Column(db.Text, nullable=True)  # Keep for backward compatibility
    # New fields for image storage
    image_url = db.Column(db.String(500), nullable=True)
    blob_name = db.Column(db.String(200), nullable=True)
    # Relationship to comments
    scan_comments = db.relationship('ScanComment', backref='scan', lazy=True, cascade='all, delete-orphan')

class ScanComment(db.Model):
    __tablename__ = 'scan_comments'
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey('scans.id'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 