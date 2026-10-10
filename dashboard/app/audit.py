"""Journal d'audit : toute modification passe par `audit(...)`."""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlmodel import Session

from .auth import CurrentUser
from .models import AuditLog

logger = logging.getLogger("hackcure.audit")


def audit(
    session: Session,
    user: CurrentUser | str | None,
    action: str,
    entity: str,
    entity_id: Any = None,
    details: Any = None,
) -> AuditLog:
    if isinstance(user, CurrentUser):
        username, role = user.username, user.role
    else:
        username, role = (user or "system"), ""
    if details is not None and not isinstance(details, str):
        details = json.dumps(details, ensure_ascii=False, default=str)
    row = AuditLog(user=username, role=role, action=action, entity=entity, entity_id=str(entity_id) if entity_id is not None else None, details=details or "")
    session.add(row)
    logger.info("AUDIT %s %s %s#%s", username, action, entity, entity_id)
    return row
