"""Add image storage fields

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add image storage fields to scans table
    op.add_column('scans', sa.Column('image_url', sa.String(length=500), nullable=True))
    op.add_column('scans', sa.Column('blob_name', sa.String(length=200), nullable=True))


def downgrade():
    # Remove image storage fields from scans table
    op.drop_column('scans', 'blob_name')
    op.drop_column('scans', 'image_url') 