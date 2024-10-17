from datetime import datetime
from uuid import uuid4
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    comments = db.relationship('Comment', back_populates='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

class Case(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    photo = db.Column(db.String(200))
    location = db.Column(db.String(100), nullable=False)
    need = db.Column(db.String(200))
    status = db.Column(db.String(20), default='OPEN')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('cases', lazy=True))
    comments = db.relationship('Comment', back_populates='case', lazy='dynamic',
                             order_by="desc(Comment.created_at)")
    
    def __repr__(self):
        return f'<Case {self.id}: {self.title}>'
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    case_id = db.Column(db.String(36), db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relationships
    case = db.relationship('Case', back_populates='comments')
    user = db.relationship('User', back_populates='comments')