from __future__ import annotations

import json
from typing import Any, Callable, Optional


def _now() -> str:
    import datetime
    return datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class AuditLog:
    """
    Minimal audit log for Phase D.3.

    Persists rows into the audit_log table created by the v2 migration.
    This is intentionally small: good enough for recording operator actions
    or worker events if you choose to call it.
    """

    def __init__(self, session_factory: Callable[[], Any]):
        self.sf = session_factory

    def record(
        self,
        action: str,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        target_id: Optional[str] = None,
        result: str = "ok",
        payload: Optional[dict] = None,
        error: Optional[dict] = None,
    ) -> None:
        ts = _now()
        with self.sf() as con:
            cur = con.cursor()
            cur.execute(
                """
                INSERT INTO audit_log(
                    ts,
                    actor_id,
                    actor_role,
                    action,
                    target_id,
                    result,
                    payload_json,
                    error_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    actor_id,
                    actor_role,
                    action,
                    target_id,
                    result,
                    json.dumps(payload) if payload is not None else None,
                    json.dumps(error) if error is not None else None,
                ),
            )
            con.commit()
