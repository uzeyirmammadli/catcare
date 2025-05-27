"""add resolved_at column

Revision ID: add_resolved_at
Revises: 
Create Date: 2025-01-27
"""

from alembic import op
import sqlalchemy as sa

revision = 'add_resolved_at'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.add_column(sa.Column('resolved_at', sa.DateTime(), nullable=True))

def downgrade():
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.drop_column('resolved_at')