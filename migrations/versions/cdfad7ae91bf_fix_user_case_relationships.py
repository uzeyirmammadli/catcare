"""fix user case relationships

Revision ID: cdfad7ae91bf
Revises: baf80c0c2682
Create Date: 2025-01-29 23:37:16.295360

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cdfad7ae91bf'
down_revision = 'baf80c0c2682'
branch_labels = None
depends_on = None


def upgrade():
    # Drop existing foreign key if it exists (safely)
    op.execute('ALTER TABLE "case" DROP CONSTRAINT IF EXISTS case_resolved_by_id_fkey')
    
    # Add foreign key constraint
    op.create_foreign_key(
        'case_resolved_by_id_fkey',
        'case', 'user',
        ['resolved_by_id'], ['id']
    )


def downgrade():
    # Drop foreign key constraint
    op.drop_constraint('case_resolved_by_id_fkey', 'case', type_='foreignkey')
