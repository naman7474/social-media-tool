from __future__ import annotations

from sqlalchemy.orm import Session

from vak_bot.db.models import AuditLog


def write_audit_log(
    db: Session,
    action: str,
    brand_id: int | None = None,
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    details: dict | None = None,
) -> AuditLog:
    log = AuditLog(
        action=action,
        brand_id=brand_id,
        user_id=user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        details_json=details,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
