"""add_pdfs_column

Revision ID: 416218f27ff7
Revises: add_resolved_at
Create Date: 2025-01-28 16:36:04.939543

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '416218f27ff7'
down_revision = 'add_resolved_at'
branch_labels = None
depends_on = None


def upgrade():
    # Add pdfs column
    op.add_column('case', sa.Column('pdfs', postgresql.ARRAY(sa.String()), nullable=True))

def downgrade():
    # Remove pdfs column
    op.drop_column('case', 'pdfs')
    
    # ### end Alembic commands ###
