"""enhance user model

Revision ID: 07d9b8d5a465
Revises: cdfad7ae91bf
Create Date: 2025-01-30 22:26:10.659095

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '07d9b8d5a465'
down_revision = 'cdfad7ae91bf'
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns only
    op.add_column('user', sa.Column('first_name', sa.String(50), nullable=True))
    op.add_column('user', sa.Column('last_name', sa.String(50), nullable=True))
    op.add_column('user', sa.Column('bio', sa.Text(), nullable=True))
    op.add_column('user', sa.Column('join_date', sa.DateTime(), nullable=True))

def downgrade():
    # Drop new columns
    op.drop_column('user', 'join_date')
    op.drop_column('user', 'bio')
    op.drop_column('user', 'last_name')
    op.drop_column('user', 'first_name')