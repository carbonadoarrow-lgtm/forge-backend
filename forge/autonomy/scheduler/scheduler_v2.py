from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass
class SchedulerCaps:
    max_total_ticks_per_invocation: int = 20
    max_ticks_per_run_per_invocation: int = 10
    daily_tick_cap: int = 2000


class SchedulerV2:
    """
    Minimal scheduler for Phase D.3:
    - picks next queued/running run in env+lane, FIFO by created_at
    - enforces simple per-invocation tick caps
    """

    def __init__(self, session_factory: Callable[[], Any]):
        self.sf = session_factory

    def next_run_id(self, env: str, lane: str) -> Optional[str]:
        with self.sf() as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT run_id
                FROM runs_v2
                WHERE env = ? AND lane = ? AND status IN ('queued', 'running')
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (env, lane),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def enforce_caps(self, env: str, lane: str, caps: SchedulerCaps, ticks_used: int) -> None:
        if ticks_used >= caps.max_total_ticks_per_invocation:
            raise RuntimeError("invocation_tick_cap_reached")
