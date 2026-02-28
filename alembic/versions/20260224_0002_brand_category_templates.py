"""add brand category templates

Revision ID: 20260224_0002
Revises: 20260224_0001
Create Date: 2026-02-24 11:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect


revision: str = "20260224_0002"
down_revision: Union[str, None] = "20260224_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table_name: str) -> bool:
    bind = op.get_bind()
    return table_name in inspect(bind).get_table_names()


def _index_names(table_name: str) -> set[str]:
    bind = op.get_bind()
    inspector = inspect(bind)
    if table_name not in inspector.get_table_names():
        return set()
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    if not _has_table("brand_category_templates"):
        op.create_table(
            "brand_category_templates",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("category", sa.String(length=50), nullable=False),
            sa.Column("template_json", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )

    index_names = _index_names("brand_category_templates")
    if "ix_brand_category_templates_category" not in index_names:
        op.create_index("ix_brand_category_templates_category", "brand_category_templates", ["category"], unique=False)
    if "ix_brand_category_templates_category_active" not in index_names:
        op.create_index(
            "ix_brand_category_templates_category_active",
            "brand_category_templates",
            ["category", "is_active"],
            unique=False,
        )


def downgrade() -> None:
    if _has_table("brand_category_templates"):
        op.drop_table("brand_category_templates")
