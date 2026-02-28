"""add brand category and description

Revision ID: 20260224_0001
Revises: 20260223_0002
Create Date: 2026-02-24T01:44:58.065890
"""
from alembic import op
import sqlalchemy as sa

revision = '20260224_0001'
down_revision = '20260223_0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add category and description to brands table
    op.add_column('brands', sa.Column('category', sa.String(50), nullable=True))
    op.add_column('brands', sa.Column('description', sa.Text(), nullable=True))
    
    # Set default category for existing brands
    op.execute("UPDATE brands SET category = 'fashion' WHERE category IS NULL")
    
    # Make category NOT NULL with default
    op.alter_column('brands', 'category', nullable=False, server_default='general')


def downgrade() -> None:
    op.drop_column('brands', 'description')
    op.drop_column('brands', 'category')
