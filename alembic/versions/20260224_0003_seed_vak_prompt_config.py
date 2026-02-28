"""seed default prompt config for backward compatibility

Revision ID: 20260224_0003
Revises: 20260224_0002
Create Date: 2026-02-24 11:20:00
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "20260224_0003"
down_revision: Union[str, None] = "20260224_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _load_default_config() -> dict:
    config_path = Path(__file__).resolve().parents[2] / "prompts" / "brand_config.json"
    if not config_path.exists():
        return {}
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def upgrade() -> None:
    bind = op.get_bind()
    brand_row = bind.execute(sa.text("SELECT id FROM brands WHERE slug = 'default' ORDER BY id LIMIT 1")).first()
    if not brand_row:
        return

    brand_id = int(brand_row[0])
    existing = bind.execute(
        sa.text(
            """
            SELECT id
            FROM brand_prompt_configs
            WHERE brand_id = :brand_id
            ORDER BY id
            LIMIT 1
            """
        ),
        {"brand_id": brand_id},
    ).first()
    if existing:
        return

    default_config = _load_default_config()
    if not default_config:
        return

    prompt_configs = sa.table(
        "brand_prompt_configs",
        sa.column("brand_id", sa.Integer()),
        sa.column("config_json", sa.JSON()),
        sa.column("is_active", sa.Boolean()),
    )
    bind.execute(
        sa.insert(prompt_configs).values(
            brand_id=brand_id,
            config_json=default_config,
            is_active=True,
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    brand_row = bind.execute(sa.text("SELECT id FROM brands WHERE slug = 'default' ORDER BY id LIMIT 1")).first()
    if not brand_row:
        return
    brand_id = int(brand_row[0])
    bind.execute(sa.text("DELETE FROM brand_prompt_configs WHERE brand_id = :brand_id"), {"brand_id": brand_id})
