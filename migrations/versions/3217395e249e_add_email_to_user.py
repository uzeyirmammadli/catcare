"""add email to user

Revision ID: 3217395e249e
Revises: 07d9b8d5a465
Create Date: 2025-01-30 22:52:28.141956

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '3217395e249e'
down_revision = '07d9b8d5a465'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user', sa.Column('email', sa.String(120), nullable=True))
    op.create_unique_constraint('uq_user_email', 'user', ['email'])

def downgrade():
    op.drop_constraint('uq_user_email', 'user', type_='unique')
    op.drop_column('user', 'email')
