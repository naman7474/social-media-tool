"""Seed brand_category_templates with category starter templates.

Usage:
    python seed_category_templates.py
"""

from __future__ import annotations

from vak_bot.db.models import BrandCategoryTemplate
from vak_bot.db.session import SessionLocal
from vak_bot.schemas.brand_config import get_category_template_map


def seed_category_templates() -> None:
    templates = get_category_template_map()
    with SessionLocal() as db:
        inserted = 0
        updated = 0

        for category, template_json in templates.items():
            row = (
                db.query(BrandCategoryTemplate)
                .filter(BrandCategoryTemplate.category == category, BrandCategoryTemplate.is_active.is_(True))
                .order_by(BrandCategoryTemplate.id.desc())
                .first()
            )
            if row is None:
                db.add(
                    BrandCategoryTemplate(
                        category=category,
                        template_json=template_json,
                        is_active=True,
                    )
                )
                inserted += 1
            else:
                row.template_json = template_json
                row.is_active = True
                updated += 1

        db.commit()

    print(f"Seed complete. inserted={inserted} updated={updated}")


if __name__ == "__main__":
    seed_category_templates()
