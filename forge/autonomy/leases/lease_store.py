from __future__ import annotations

from typing import Any, Callable


def _now_iso() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _now_epoch() -> int:
    import time
    return int(time.time())


def _iso_from_epoch(ts: int) -> str:
    import datetime
    return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _epoch_from_iso(iso: str) -> int:
    import datetime
    iso = iso.replace("Z", "")
    dt = datetime.datetime.fromisoformat(iso)
    return int(dt.timestamp())


class LeaseStore:
    """
    Minimal lease store for Phase D.3:
    - single-owner lease per run_id
    - simple TTL-based expiration
    """

    def __init__(self, session_factory: Callable[[], Any]):
        self.sf = session_factory

    def acquire(self, run_id: str, owner_id: str, ttl_seconds: int) -> bool:
        now = _now_epoch()
        with self.sf() as con:
            # Use BEGIN IMMEDIATE to prevent race condition
            # This ensures atomicity: check + acquire happens in single transaction
            con.execute("BEGIN IMMEDIATE")
            try:
                cur = con.cursor()
                cur.execute("SELECT owner_id, expires_at FROM leases_v2 WHERE run_id = ?", (run_id,))
                row = cur.fetchone()
                if row:
                    _, expires_at = row
                    if _epoch_from_iso(expires_at) > now:
                        # active lease held by someone else
                        con.rollback()
                        return False
                acquired_at = _now_iso()
                expires_at = _iso_from_epoch(now + ttl_seconds)
                cur.execute(
                    """
                    INSERT OR REPLACE INTO leases_v2(run_id, owner_id, acquired_at, renewed_at, expires_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (run_id, owner_id, acquired_at, acquired_at, expires_at),
                )
                con.commit()
                return True
            except Exception as e:
                con.rollback()
                raise

    def renew(self, run_id: str, owner_id: str, ttl_seconds: int) -> bool:
        now = _now_epoch()
        with self.sf() as con:
            cur = con.cursor()
            cur.execute("SELECT owner_id FROM leases_v2 WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row or row[0] != owner_id:
                return False
            renewed_at = _now_iso()
            expires_at = _iso_from_epoch(now + ttl_seconds)
            cur.execute(
                "UPDATE leases_v2 SET renewed_at = ?, expires_at = ? WHERE run_id = ?",
                (renewed_at, expires_at, run_id),
            )
            con.commit()
            return True

    def release(self, run_id: str, owner_id: str) -> None:
        with self.sf() as con:
            cur = con.cursor()
            cur.execute("DELETE FROM leases_v2 WHERE run_id = ? AND owner_id = ?", (run_id, owner_id))
            con.commit()
