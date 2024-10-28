import random
from datetime import datetime
from uuid import uuid4
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from . import db


def init_db():
    """Initialize database and create tables."""
    db.create_all()
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

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
    @classmethod
    def get_by_status(cls, status):
        """Retrieve cases by status."""
        status = status.upper()
        if status not in ["OPEN", "RESOLVED"]:
            raise ValueError("Invalid status. Please provide 'OPEN' or 'RESOLVED'.")
        return cls.query.filter_by(status=status).all()
    
    @classmethod
    def get_by_location(cls, location):
        if not location:
            raise ValueError("Location cannot be empty")
        return cls.query.filter_by(location=location).all()
    
    def update_case(self, case_id, photo=None, location=None, need=None, status=None):
        """Update case details"""
        case = self.query.get(case_id)
        if not case:
            raise ValueError("Case not found")
        case.photo = photo or case.photo
        case.location = location or case.location
        case.need = need or case.need
        case.status = status or case.status
        case.updated_at = datetime.utcnow()
        db.session.commit()

    def resolve(self, case_id):
        """Mark case as resolved."""
        case = self.query.get(case_id)
        if not case:
            raise ValueError("Case not found")
        case.status = 'RESOLVED'
        case.updated_at = datetime.utcnow()
        db.session.commit()

    @classmethod
    def delete_case(cls, case_id):
        case = cls.query.get(case_id)
        if not case:
            raise ValueError("Case not found")
        db.session.delete(case)
        db.session.commit()
        return True
    
    def to_dict(self):
        """Convert case to dictionary representation."""
        return {
            'id': self.id,
            'photo': self.photo,
            'location': self.location,
            'need': self.need,
            'status': self.status,
            'created_at': self.created_at.strftime('%A %d %B %Y, %I:%M%p'),
            'updated_at': self.updated_at.strftime('%A %d %B %Y, %I:%M%p')
        }
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

    def __repr__(self):
        return f'<Comment {self.id} on Case {self.case_id}>'
    
def seed_database():
    try:
        locations = ['Nasirov', 'Rajabli', 'Mayakovski']
        test_user = User.query.filter_by(username='testuser').first()

        if not test_user:
            test_user = User(username='testuser')
            test_user.set_password('testpassword')
            db.session.add(test_user)

        for _ in range(9):
            case = Case(
                photo='https://picsum.photos/200/300',
                location=random.choice(locations),
                need='Medicine',
                status='OPEN',
                user_id=test_user.id
            )
            db.session.add(case)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        raise e
