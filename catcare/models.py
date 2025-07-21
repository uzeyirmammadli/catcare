import random
import json
from datetime import datetime
from uuid import uuid4
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.sql import func
from . import db


class DatabaseAwareArrayType(TypeDecorator):
    """Database-aware array type that uses ARRAY for PostgreSQL and JSON for SQLite."""

    impl = Text  # Default implementation for SQLAlchemy
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Choose implementation based on database dialect."""
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(String))
        else:
            return dialect.type_descriptor(Text)

    def process_bind_param(self, value, dialect):
        """Convert Python list for storage based on database type."""
        if value is None:
            return None
        
        if dialect.name == 'postgresql':
            # PostgreSQL handles arrays natively
            # Handle transition from JSON strings to arrays
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return []
            return value if isinstance(value, list) else []
        else:
            # SQLite and others: store as JSON string
            if isinstance(value, list):
                return json.dumps(value)
            return value

    def process_result_value(self, value, dialect):
        """Convert stored value back to Python list."""
        if value is None:
            return []
        
        if dialect.name == 'postgresql':
            # PostgreSQL returns arrays directly
            return value if isinstance(value, list) else []
        else:
            # SQLite and others: parse JSON string
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return []
            return value if isinstance(value, list) else []


def init_db():
    """Initialize database and create tables."""
    db.create_all()


class User(UserMixin, db.Model):
    """Represents a user in the system."""

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    bio = db.Column(db.Text)
    join_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Role-based access control
    role = db.Column(db.String(20), default='REPORTER', nullable=False)  # ADMIN, VOLUNTEER, REPORTER
    
    # Account verification
    is_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(100), unique=True)
    verification_sent_at = db.Column(db.DateTime)
    
    # OAuth integration
    oauth_provider = db.Column(db.String(50))  # google, facebook, etc.
    oauth_id = db.Column(db.String(100))
    
    # Session management
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # JWT token management
    jwt_refresh_token = db.Column(db.String(500))
    jwt_refresh_expires = db.Column(db.DateTime)
    
    # Language preference
    language = db.Column(db.String(5), default='en')

    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the stored hash."""
        return check_password_hash(self.password_hash, password)
    
    # Role-based access control methods
    def has_role(self, role):
        """Check if user has a specific role."""
        return self.role == role.upper()
    
    def is_admin(self):
        """Check if user is an admin."""
        return self.role == 'ADMIN'
    
    def is_volunteer(self):
        """Check if user is a volunteer."""
        return self.role == 'VOLUNTEER'
    
    def is_reporter(self):
        """Check if user is a reporter."""
        return self.role == 'REPORTER'
    
    def can_edit_case(self, case):
        """Check if user can edit a specific case."""
        return self.is_admin() or self.id == case.user_id
    
    def can_resolve_case(self, case):
        """Check if user can resolve a case."""
        return self.is_admin() or self.is_volunteer()
    
    def can_delete_case(self, case):
        """Check if user can delete a case."""
        return self.is_admin() or self.id == case.user_id
    
    # Account verification methods
    def generate_verification_token(self):
        """Generate a verification token for email verification."""
        import secrets
        self.verification_token = secrets.token_urlsafe(32)
        self.verification_sent_at = datetime.utcnow()
        return self.verification_token
    
    def verify_account(self, token):
        """Verify account with token."""
        if self.verification_token == token:
            self.is_verified = True
            self.verification_token = None
            return True
        return False
    
    # JWT token methods
    def generate_jwt_refresh_token(self):
        """Generate JWT refresh token."""
        import secrets
        from datetime import timedelta
        self.jwt_refresh_token = secrets.token_urlsafe(64)
        self.jwt_refresh_expires = datetime.utcnow() + timedelta(days=30)
        return self.jwt_refresh_token
    
    def is_jwt_refresh_valid(self):
        """Check if JWT refresh token is still valid."""
        return (self.jwt_refresh_token and 
                self.jwt_refresh_expires and 
                self.jwt_refresh_expires > datetime.utcnow())
    
    # Session management
    def update_last_login(self):
        """Update last login timestamp."""
        self.last_login = datetime.utcnow()
    
    def deactivate(self):
        """Deactivate user account."""
        self.is_active = False
    
    def activate(self):
        """Activate user account."""
        self.is_active = True

    comments = db.relationship(
        "Comment", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    # Cases created by the user
    cases = db.relationship("Case", backref="user", foreign_keys="Case.user_id", lazy=True)

    # Cases resolved by the user
    resolved_cases = db.relationship(
        "Case", backref="resolved_by", foreign_keys="Case.resolved_by_id", lazy=True
    )

    def __repr__(self):
        return f"<User {self.username}>"


class Case(db.Model):
    """Represents a case in the system."""

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    photos = db.Column(DatabaseAwareArrayType(), default=list)
    videos = db.Column(DatabaseAwareArrayType(), default=list)
    needs = db.Column(DatabaseAwareArrayType(), default=list)
    photo = db.Column(db.String(200))  # Keep for migration
    location = db.Column(db.String(500), nullable=False, index=True)
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    need = db.Column(db.String(200))  # Keep for migration
    status = db.Column(db.String(20), default="OPEN", index=True)
    resolution_notes = db.Column(db.Text())
    resolution_photos = db.Column(DatabaseAwareArrayType(), default=list)  # Photos added during resolution
    resolution_videos = db.Column(DatabaseAwareArrayType(), default=list)
    pdfs = db.Column(DatabaseAwareArrayType(), default=list)
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolved_by_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    comments = db.relationship(
        "Comment", back_populates="case", lazy="dynamic", cascade="all, delete-orphan"
    )

    @staticmethod
    def validate_status(status):
        """Validate the status field."""
        if status not in ["OPEN", "RESOLVED"]:
            raise ValueError("Status must be 'OPEN' or 'RESOLVED'.")

    def __init__(self, **kwargs):
        """Initialize a case with validated status."""
        self.validate_status(kwargs.get("status", "OPEN"))
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

    def update_case(
        self, case_id, photos=None, videos=None, location=None, needs=None, status=None
    ):
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
        case.status = "RESOLVED"
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
            "id": self.id,
            "photos": self.photos,
            "videos": self.videos,
            "needs": self.needs,
            "location": self.location,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "status": self.status,
            "resolution_notes": self.resolution_notes,
            "created_at": self.created_at.strftime("%A %d %B %Y, %I:%M%p"),
            "updated_at": self.updated_at.strftime("%A %d %B %Y, %I:%M%p"),
            "user_id": self.user_id,
        }

    def __repr__(self):
        return f"<Case {self.id}: {self.location}>"


class Comment(db.Model):
    """Represents a comment on a case."""

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    # Foreign keys
    case_id = db.Column(db.String(36), db.ForeignKey("case.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Relationships
    case = db.relationship("Case", back_populates="comments")
    user = db.relationship("User", back_populates="comments")

    def __repr__(self):
        return f"<Comment {self.id} on Case {self.case_id}>"


class SavedSearch(db.Model):
    """Represents a saved search preference for a user."""

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(500))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    radius = db.Column(db.Float, default=5.0)
    status = db.Column(db.String(20))
    needs = db.Column(DatabaseAwareArrayType(), default=list)
    date_from = db.Column(db.Date)
    date_to = db.Column(db.Date)
    sort_by = db.Column(db.String(50), default="created_at")
    sort_order = db.Column(db.String(10), default="desc")
    is_default = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=func.now(), onupdate=func.now())

    # Foreign key
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

    # Relationship
    user = db.relationship("User", backref="saved_searches")

    def to_dict(self):
        """Convert saved search to dictionary for easy use in templates."""
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'radius': self.radius,
            'status': self.status,
            'needs': self.needs or [],
            'date_from': self.date_from.strftime('%Y-%m-%d') if self.date_from else '',
            'date_to': self.date_to.strftime('%Y-%m-%d') if self.date_to else '',
            'sort_by': self.sort_by,
            'sort_order': self.sort_order,
            'is_default': self.is_default
        }

    def __repr__(self):
        return f"<SavedSearch {self.name} by User {self.user_id}>"


def seed_database():
    """Seed the database with test data."""
    try:
        locations = ["Nasirov", "Rajabli", "Mayakovski"]
        test_user = User.query.filter_by(username="testuser").first()

        if not test_user:
            test_user = User(username="testuser")
            test_user.set_password("testpassword")
            db.session.add(test_user)

        for _ in range(9):
            case = Case(
                photo="https://picsum.photos/200/300",
                location=random.choice(locations),
                need="Medicine",
                status="OPEN",
                user_id=test_user.id,
            )
            db.session.add(case)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding database: {e}")
        raise
