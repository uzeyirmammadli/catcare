#!/usr/bin/env python3
"""
Migration script to add advanced authentication fields to User model
"""

import sys
import os
sys.path.append('.')

from catcare import create_app
from catcare.models import db, User
from sqlalchemy import text

def add_auth_fields():
    """Add new authentication fields to User table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('user')]
            
            # Add new columns if they don't exist
            new_columns = [
                ('role', 'ALTER TABLE "user" ADD COLUMN role VARCHAR(20) DEFAULT \'REPORTER\' NOT NULL'),
                ('is_verified', 'ALTER TABLE "user" ADD COLUMN is_verified BOOLEAN DEFAULT FALSE'),
                ('verification_token', 'ALTER TABLE "user" ADD COLUMN verification_token VARCHAR(100) UNIQUE'),
                ('verification_sent_at', 'ALTER TABLE "user" ADD COLUMN verification_sent_at TIMESTAMP'),
                ('oauth_provider', 'ALTER TABLE "user" ADD COLUMN oauth_provider VARCHAR(50)'),
                ('oauth_id', 'ALTER TABLE "user" ADD COLUMN oauth_id VARCHAR(100)'),
                ('last_login', 'ALTER TABLE "user" ADD COLUMN last_login TIMESTAMP'),
                ('is_active', 'ALTER TABLE "user" ADD COLUMN is_active BOOLEAN DEFAULT TRUE'),
                ('jwt_refresh_token', 'ALTER TABLE "user" ADD COLUMN jwt_refresh_token VARCHAR(500)'),
                ('jwt_refresh_expires', 'ALTER TABLE "user" ADD COLUMN jwt_refresh_expires TIMESTAMP')
            ]
            
            for column_name, sql in new_columns:
                if column_name not in existing_columns:
                    print(f"Adding column: {column_name}")
                    db.session.execute(text(sql))
                else:
                    print(f"Column {column_name} already exists, skipping...")
            
            # Update existing users to have default role and be active
            db.session.execute(text("""
                UPDATE "user" 
                SET role = 'REPORTER', is_active = TRUE 
                WHERE role IS NULL OR is_active IS NULL
            """))
            
            db.session.commit()
            print("Migration completed successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    add_auth_fields()