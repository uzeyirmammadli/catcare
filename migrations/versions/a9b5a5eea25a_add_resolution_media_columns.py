"""add_resolution_media_columns

Revision ID: a9b5a5eea25a
Revises: 416218f27ff7
Create Date: 2025-01-29 15:04:34.243141

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a9b5a5eea25a'
down_revision = '416218f27ff7'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns
    op.add_column('case', sa.Column('resolution_photos', postgresql.ARRAY(sa.String()), nullable=True))
    op.add_column('case', sa.Column('resolution_videos', postgresql.ARRAY(sa.String()), nullable=True))


def downgrade():
    # Remove the columns
    op.drop_column('case', 'resolution_photos')
    op.drop_column('case', 'resolution_videos')
