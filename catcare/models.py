import random
from datetime import datetime
from uuid import uuid4
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String
from sqlalchemy.sql import func
from . import db


def init_db():
    """Initialize database and create tables."""
    db.create_all()


class User(UserMixin, db.Model):
    """Represents a user in the system."""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)

    comments = db.relationship('Comment', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")
    cases = db.relationship('Case', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.username}>'


class Case(db.Model):
    """Represents a case in the system."""
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    photos = db.Column(ARRAY(db.String), default=[])
    videos = db.Column(ARRAY(db.String), default=[])
    needs = db.Column(ARRAY(db.String), default=[])
    photo = db.Column(db.String(200))  # Keep for migration
    location = db.Column(db.String(500), nullable=False, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    need = db.Column(db.String(200))   # Keep for migration
    status = db.Column(db.String(20), default='OPEN', index=True)
    resolution_notes = db.Column(db.Text())
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', back_populates='case', lazy='dynamic', cascade="all, delete-orphan")

    @staticmethod
    def validate_status(status):
        """Validate the status field."""
        if status not in ["OPEN", "RESOLVED"]:
            raise ValueError("Status must be 'OPEN' or 'RESOLVED'.")

    def __init__(self, **kwargs):
        """Initialize a case with validated status."""
        self.validate_status(kwargs.get('status', 'OPEN'))
        super().__init__(**kwargs)

    @classmethod
    def get_by_status(cls, status):
        """Retrieve cases by status."""
        status = status.upper()
        if status not in ["OPEN", "RESOLVED"]:
            raise ValueError("Invalid status. Please provide 'OPEN' or 'RESOLVED'.")
        return cls.query.filter_by(status=status).all()

    @classmethod
    def get_by_location(cls, location):
        """Retrieve cases by location."""
        if not location:
            raise ValueError("Location cannot be empty")
        return cls.query.filter_by(location=location).all()

    def update_case(self, case_id, photos=None, videos=None, location=None, needs=None, status=None):
        """Update case details."""
        case = self.query.get(case_id)
        if not case:
            raise ValueError("Case not found")

        if photos is not None:
            case.photos = photos
        if videos is not None:
            case.videos = videos
        if location is not None:
            case.location = location
        if needs is not None:
            case.needs = needs
        if status is not None:
            case.status = status

        case.updated_at = func.now()
        db.session.commit()

    def resolve(self, case_id):
        """Mark case as resolved."""
        case = self.query.get(case_id)
        if not case:
            raise ValueError("Case not found")
        case.status = 'RESOLVED'
        case.updated_at = func.now()
        db.session.commit()

    @classmethod
    def delete_case(cls, case_id):
        """Delete a case by ID."""
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
            'photos': self.photos,
            'videos': self.videos,
            'needs': self.needs,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'status': self.status,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.strftime('%A %d %B %Y, %I:%M%p'),
            'updated_at': self.updated_at.strftime('%A %d %B %Y, %I:%M%p'),
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<Case {self.id}: {self.location}>'


class Comment(db.Model):
    """Represents a comment on a case."""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    # Foreign keys
    case_id = db.Column(db.String(36), db.ForeignKey('case.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    # Relationships
    case = db.relationship('Case', back_populates='comments')
    user = db.relationship('User', back_populates='comments')

    def __repr__(self):
        return f'<Comment {self.id} on Case {self.case_id}>'


def seed_database():
    """Seed the database with test data."""
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
        print(f"Error seeding database: {e}")
        raise