from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List


def _now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class Event:
    def __init__(self, run_id: str, ts: str, event_type: str, payload: Dict[str, Any]):
        self.run_id = run_id
        self.ts = ts
        self.event_type = event_type
        self.payload = payload


class EventBusV2:
    """
    Minimal event bus for Phase D.3:
    - persists events to run_events_v2
    - supports replay(run_id)
    - optional in-process subscribe(run_id) for SSE/etc.
    """

    def __init__(self, session_factory: Callable[[], Any]):
        self.sf = session_factory
        self._queues: Dict[str, "asyncio.Queue[Event]"] = {}

    def publish(self, run_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        evt = Event(run_id=run_id, ts=_now(), event_type=event_type, payload=payload)
        with self.sf() as con:
            cur = con.cursor()
            cur.execute(
                "INSERT INTO run_events_v2(run_id, ts, event_type, payload_json) VALUES (?, ?, ?, ?)",
                (run_id, evt.ts, evt.event_type, json.dumps(evt.payload)),
            )
            con.commit()

        q = self._queues.get(run_id)
        if q:
            try:
                q.put_nowait(evt)
            except Exception:
                # best-effort only
                pass

    def replay(self, run_id: str, limit: int = 200) -> List[Event]:
        with self.sf() as con:
            cur = con.cursor()
            cur.execute(
                "SELECT ts, event_type, payload_json FROM run_events_v2 WHERE run_id = ? ORDER BY ts ASC LIMIT ?",
                (run_id, limit),
            )
            rows = cur.fetchall()

        out: List[Event] = []
        for ts, etype, payload_json in rows:
            try:
                payload = json.loads(payload_json)
            except Exception:
                payload = {"raw": payload_json}
            out.append(Event(run_id, ts, etype, payload))
        return out

    async def subscribe(self, run_id: str):
        """
        Async generator yielding events for given run_id.
        Intended for SSE; not required for Phase D.3 proof.
        """
        q = self._queues.setdefault(run_id, asyncio.Queue())
        while True:
            evt = await q.get()
            yield evt
