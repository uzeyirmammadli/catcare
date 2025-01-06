"""initial_migration

Revision ID: f0a4a9fa70cb
Revises: 
Create Date: 2024-12-24 17:34:36.946900

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f0a4a9fa70cb'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Add array columns and location columns to case table
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.add_column(sa.Column('photos', postgresql.ARRAY(sa.String()), nullable=True, server_default='{}'))
        batch_op.add_column(sa.Column('videos', postgresql.ARRAY(sa.String()), nullable=True, server_default='{}'))
        batch_op.add_column(sa.Column('needs', postgresql.ARRAY(sa.String()), nullable=True, server_default='{}'))

def downgrade():
    with op.batch_alter_table('case', schema=None) as batch_op:
        batch_op.drop_column('needs')
        batch_op.drop_column('videos')
        batch_op.drop_column('photos')