from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime


# =========================================
# DATABASE OBJECT
# =========================================

db = SQLAlchemy()


# =========================================
# USER MODEL
# =========================================

class User(db.Model, UserMixin):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password_hash = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# =========================================
# DOCUMENT MODEL
# =========================================

class Document(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # Original filename shown in the application
    filename = db.Column(
        db.String(255),
        nullable=False
    )

    # Actual unique filename stored inside uploads/
    stored_filename = db.Column(
        db.String(255),
        nullable=True
    )

    upload_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    chunk_count = db.Column(
        db.Integer,
        default=0
    )

    # User who owns this document
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )


# =========================================
# CHAT HISTORY MODEL
# =========================================

class ChatHistory(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    document_id = db.Column(
        db.Integer,
        db.ForeignKey("document.id"),
        nullable=False
    )

    question = db.Column(
        db.Text,
        nullable=False
    )

    answer = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )