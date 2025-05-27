"""add resolved_by to case

Revision ID: baf80c0c2682
Revises: a9b5a5eea25a
Create Date: 2025-01-29 23:16:38.907961

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'baf80c0c2682'
down_revision = 'a9b5a5eea25a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('case', sa.Column('resolved_by_id', sa.Integer(), sa.ForeignKey('user.id')))

def downgrade():
    op.drop_column('case', 'resolved_by_id')
