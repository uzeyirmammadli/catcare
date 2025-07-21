#!/usr/bin/env python3
"""
Migration script to add language preference field to User model
"""

import sys
import os
sys.path.append('.')

from catcare import create_app
from catcare.models import db
from sqlalchemy import text

def add_language_field():
    """Add language field to User table"""
    app = create_app()
    
    with app.app_context():
        try:
            # Check if column already exists
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'language' not in existing_columns:
                print("Adding language column to user table...")
                db.session.execute(text('ALTER TABLE "user" ADD COLUMN language VARCHAR(5) DEFAULT \'en\''))
                
                # Update existing users to have default language
                db.session.execute(text('UPDATE "user" SET language = \'en\' WHERE language IS NULL'))
                
                db.session.commit()
                print("Language field added successfully!")
            else:
                print("Language column already exists, skipping...")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {str(e)}")
            raise

if __name__ == "__main__":
    add_language_field()