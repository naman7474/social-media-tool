"""add_video_columns_and_jobs

Revision ID: 2b664509a956
Revises: 20260221_0001
Create Date: 2026-02-22 16:59:25.511556
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "2b664509a956"
down_revision: Union[str, None] = "20260221_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return table_name in inspect(bind).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return False
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("video_jobs"):
        op.create_table(
            "video_jobs",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("post_id", sa.Integer(), nullable=False),
            sa.Column("veo_operation_id", sa.String(length=200), nullable=True),
            sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
            sa.Column("variation_number", sa.Integer(), nullable=False),
            sa.Column("video_url", sa.String(length=500), nullable=True),
            sa.Column("generation_time_seconds", sa.Integer(), nullable=True),
            sa.Column("prompt_used", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"]),
            sa.PrimaryKeyConstraint("id"),
        )

    for name, col in [
        ("detected_media_type", sa.Column("detected_media_type", sa.String(length=10), nullable=True)),
        ("video_url", sa.Column("video_url", sa.String(length=500), nullable=True)),
        ("video_style_brief", sa.Column("video_style_brief", sa.JSON(), nullable=True)),
        ("video_type", sa.Column("video_type", sa.String(length=20), nullable=True)),
        ("start_frame_url", sa.Column("start_frame_url", sa.String(length=500), nullable=True)),
        ("video_duration", sa.Column("video_duration", sa.Integer(), nullable=True)),
        ("thumb_offset_ms", sa.Column("thumb_offset_ms", sa.Integer(), nullable=True)),
    ]:
        if not _has_column("posts", name):
            op.add_column("posts", col)

    idx_names = _index_names("products")
    if "ix_products_product_code" in idx_names:
        op.drop_index("ix_products_product_code", table_name="products")
    op.create_index("ix_products_product_code", "products", ["product_code"], unique=True)


def downgrade() -> None:
    # Kept intentionally lightweight; newer migrations supersede this structure.
    pass
