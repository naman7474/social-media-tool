"""multi-brand + admin schema

Revision ID: 20260223_0002
Revises: 2b664509a956
Create Date: 2026-02-23 12:00:00
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "20260223_0002"
down_revision: Union[str, None] = "2b664509a956"
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


def _get_default_brand_id() -> int:
    bind = op.get_bind()
    row = bind.execute(sa.text("SELECT id FROM brands WHERE slug = 'default' ORDER BY id LIMIT 1")).first()
    if row:
        return int(row[0])
    bind.execute(
        sa.text(
            """
            INSERT INTO brands (slug, name, timezone, status)
            VALUES ('default', 'Default Brand', 'Asia/Kolkata', 'active')
            """
        )
    )
    row = bind.execute(sa.text("SELECT id FROM brands WHERE slug = 'default' ORDER BY id LIMIT 1")).first()
    return int(row[0])


def _add_brand_id_column(table_name: str) -> None:
    if not _has_column(table_name, "brand_id"):
        op.add_column(table_name, sa.Column("brand_id", sa.Integer(), nullable=True))
        op.create_foreign_key(f"fk_{table_name}_brand_id", table_name, "brands", ["brand_id"], ["id"])


def upgrade() -> None:
    if not _has_table("brands"):
        op.create_table(
            "brands",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("slug", sa.String(length=80), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("timezone", sa.String(length=64), nullable=False, server_default="Asia/Kolkata"),
            sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
            sa.Column("telegram_bot_token", sa.String(length=255), nullable=True),
            sa.Column("telegram_webhook_secret", sa.String(length=255), nullable=True),
            sa.Column("allowed_user_ids", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("slug", name="uq_brands_slug"),
        )
        op.create_index("ix_brands_slug", "brands", ["slug"], unique=True)

    if not _has_table("brand_credentials"):
        op.create_table(
            "brand_credentials",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False),
            sa.Column("meta_app_id", sa.String(length=255), nullable=True),
            sa.Column("encrypted_meta_app_secret", sa.Text(), nullable=True),
            sa.Column("encrypted_meta_page_access_token", sa.Text(), nullable=True),
            sa.Column("instagram_business_account_id", sa.String(length=100), nullable=True),
            sa.Column("meta_graph_api_version", sa.String(length=20), nullable=False, server_default="v25.0"),
            sa.Column("meta_token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("brand_id", name="uq_brand_credentials_brand_id"),
        )
        op.create_index("ix_brand_credentials_brand_id", "brand_credentials", ["brand_id"], unique=True)

    if not _has_table("brand_prompt_configs"):
        op.create_table(
            "brand_prompt_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=False),
            sa.Column("config_json", sa.JSON(), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("brand_id", name="uq_brand_prompt_configs_brand_id"),
        )
        op.create_index("ix_brand_prompt_configs_brand_id", "brand_prompt_configs", ["brand_id"], unique=True)

    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("email", sa.String(length=255), nullable=False),
            sa.Column("password_hash", sa.String(length=255), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("email", name="uq_users_email"),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    if not _has_table("user_brand_roles"):
        op.create_table(
            "user_brand_roles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
            sa.Column("role", sa.String(length=40), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.UniqueConstraint("user_id", "brand_id", "role", name="uq_user_brand_role"),
        )
        op.create_index("ix_user_brand_roles_user_id", "user_brand_roles", ["user_id"], unique=False)
        op.create_index("ix_user_brand_roles_brand_id", "user_brand_roles", ["brand_id"], unique=False)

    if not _has_table("audit_logs"):
        op.create_table(
            "audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("brand_id", sa.Integer(), sa.ForeignKey("brands.id"), nullable=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("entity_type", sa.String(length=80), nullable=True),
            sa.Column("entity_id", sa.String(length=80), nullable=True),
            sa.Column("details_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("ix_audit_logs_brand_id", "audit_logs", ["brand_id"], unique=False)
        op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], unique=False)

    default_brand_id = _get_default_brand_id()

    for table_name in [
        "products",
        "posts",
        "product_photos",
        "telegram_sessions",
        "job_runs",
        "video_jobs",
        "post_variants",
        "post_variant_items",
    ]:
        _add_brand_id_column(table_name)

    bind = op.get_bind()
    for table_name in [
        "products",
        "posts",
        "product_photos",
        "telegram_sessions",
        "job_runs",
        "video_jobs",
        "post_variants",
        "post_variant_items",
    ]:
        bind.execute(sa.text(f"UPDATE {table_name} SET brand_id = :brand_id WHERE brand_id IS NULL"), {"brand_id": default_brand_id})
        op.alter_column(table_name, "brand_id", nullable=False)

    if not _has_column("posts", "scheduled_for"):
        op.add_column("posts", sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True))
    if not _has_column("posts", "scheduled_timezone"):
        op.add_column("posts", sa.Column("scheduled_timezone", sa.String(length=64), nullable=True))
    if not _has_column("posts", "scheduled_by_user_id"):
        op.add_column("posts", sa.Column("scheduled_by_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key("fk_posts_scheduled_by_user_id", "posts", "users", ["scheduled_by_user_id"], ["id"])

    # product uniqueness becomes (brand_id, product_code)
    idx_names = _index_names("products")
    if "ix_products_product_code" in idx_names:
        op.drop_index("ix_products_product_code", table_name="products")
    op.create_index("ix_products_product_code", "products", ["product_code"], unique=False)
    op.create_index("ix_products_brand_code", "products", ["brand_id", "product_code"], unique=True)

    # tenant session uniqueness
    op.create_unique_constraint(
        "uq_telegram_sessions_brand_user_chat",
        "telegram_sessions",
        ["brand_id", "telegram_user_id", "chat_id"],
    )

    # tenant performance indexes
    if "ix_posts_brand_status_created_at" not in _index_names("posts"):
        op.create_index("ix_posts_brand_status_created_at", "posts", ["brand_id", "status", "created_at"], unique=False)
    if "ix_job_runs_brand_status_started_at" not in _index_names("job_runs"):
        op.create_index("ix_job_runs_brand_status_started_at", "job_runs", ["brand_id", "status", "started_at"], unique=False)


def downgrade() -> None:
    raise NotImplementedError("Downgrade is intentionally not supported for this migration")
