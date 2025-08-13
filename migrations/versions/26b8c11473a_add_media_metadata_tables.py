"""add media metadata tables

Revision ID: 26b8c11473a
Revises: 07d9b8d5a465
Create Date: 2025-01-30 22:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '26b8c11473a'
down_revision = '07d9b8d5a465'
branch_labels = None
depends_on = None


def upgrade():
    # Create media_metadata table
    op.create_table('media_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.String(36), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('original_filename', sa.String(255), nullable=True),
        sa.Column('file_size_original', sa.Integer(), nullable=True),
        sa.Column('file_size_processed', sa.Integer(), nullable=True),
        sa.Column('compression_ratio', sa.Numeric(5, 2), nullable=True),
        sa.Column('format_original', sa.String(10), nullable=True),
        sa.Column('format_processed', sa.String(10), nullable=True),
        sa.Column('timestamp_original', sa.DateTime(), nullable=True),
        sa.Column('gps_latitude', sa.Numeric(10, 8), nullable=True),
        sa.Column('gps_longitude', sa.Numeric(11, 8), nullable=True),
        sa.Column('location_name', sa.String(255), nullable=True),
        sa.Column('camera_make', sa.String(100), nullable=True),
        sa.Column('camera_model', sa.String(100), nullable=True),
        sa.Column('image_width', sa.Integer(), nullable=True),
        sa.Column('image_height', sa.Integer(), nullable=True),
        sa.Column('orientation', sa.Integer(), nullable=True),
        sa.Column('processing_time', sa.Numeric(8, 3), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['case_id'], ['case.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create media_thumbnail table
    op.create_table('media_thumbnail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('media_metadata_id', sa.Integer(), nullable=False),
        sa.Column('size_label', sa.String(20), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['media_metadata_id'], ['media_metadata.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create batch_processing_log table
    op.create_table('batch_processing_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('total_files', sa.Integer(), nullable=False),
        sa.Column('successful_files', sa.Integer(), nullable=False),
        sa.Column('failed_files', sa.Integer(), nullable=False),
        sa.Column('total_size_original', sa.BigInteger(), nullable=True),
        sa.Column('total_size_processed', sa.BigInteger(), nullable=True),
        sa.Column('average_compression_ratio', sa.Numeric(5, 2), nullable=True),
        sa.Column('processing_time', sa.Numeric(8, 3), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for efficient metadata queries
    op.create_index('idx_media_metadata_case_id', 'media_metadata', ['case_id'])
    op.create_index('idx_media_metadata_filename', 'media_metadata', ['filename'])
    op.create_index('idx_media_metadata_timestamp', 'media_metadata', ['timestamp_original'])
    op.create_index('idx_media_metadata_location', 'media_metadata', ['gps_latitude', 'gps_longitude'])
    op.create_index('idx_media_metadata_camera', 'media_metadata', ['camera_make', 'camera_model'])
    op.create_index('idx_media_thumbnail_metadata_id', 'media_thumbnail', ['media_metadata_id'])
    op.create_index('idx_media_thumbnail_size', 'media_thumbnail', ['size_label'])
    op.create_index('idx_batch_log_user_id', 'batch_processing_log', ['user_id'])
    op.create_index('idx_batch_log_status', 'batch_processing_log', ['status'])
    op.create_index('idx_batch_log_started_at', 'batch_processing_log', ['started_at'])


def downgrade():
    # Drop indexes first
    op.drop_index('idx_batch_log_started_at', table_name='batch_processing_log')
    op.drop_index('idx_batch_log_status', table_name='batch_processing_log')
    op.drop_index('idx_batch_log_user_id', table_name='batch_processing_log')
    op.drop_index('idx_media_thumbnail_size', table_name='media_thumbnail')
    op.drop_index('idx_media_thumbnail_metadata_id', table_name='media_thumbnail')
    op.drop_index('idx_media_metadata_camera', table_name='media_metadata')
    op.drop_index('idx_media_metadata_location', table_name='media_metadata')
    op.drop_index('idx_media_metadata_timestamp', table_name='media_metadata')
    op.drop_index('idx_media_metadata_filename', table_name='media_metadata')
    op.drop_index('idx_media_metadata_case_id', table_name='media_metadata')
    
    # Drop tables
    op.drop_table('batch_processing_log')
    op.drop_table('media_thumbnail')
    op.drop_table('media_metadata')