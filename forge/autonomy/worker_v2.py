from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class WorkerTickSummary:
    owner_id: str
    env: str
    lane: str
    ticks_used: int
    runs_ticked: int


class WorkerV2:
    """
    Minimal worker for Phase D.3:
    - uses SchedulerV2 to select runs
    - uses LeaseStore for per-run mutual exclusion
    - calls GraphTickV2.tick_run
    - respects a kill switch (lane_enabled)
    """

    def __init__(self, scheduler: Any, leases: Any, ticker: Any, bus: Any, kill_switch: Any):
        self.scheduler = scheduler
        self.leases = leases
        self.ticker = ticker
        self.bus = bus
        self.kill_switch = kill_switch

    def _kill_active(self):
        # In this backfill kill_switch is already the object; kept flexible.
        if hasattr(self.kill_switch, "get_active"):
            return self.kill_switch.get_active()
        return self.kill_switch

    def tick_once(
        self,
        env: str,
        lane: str,
        owner_id: str,
        caps: Any,
        lease_ttl_seconds: int = 30,
    ) -> WorkerTickSummary:
        ticks_used = 0
        runs_ticked = 0

        for _ in range(caps.max_total_ticks_per_invocation):
            self.scheduler.enforce_caps(env, lane, caps, ticks_used)

            ks = self._kill_active()
            if hasattr(ks, "lane_enabled") and not ks.lane_enabled(env, lane):
                break

            run_id = self.scheduler.next_run_id(env, lane)
            if not run_id:
                break

            if not self.leases.acquire(run_id, owner_id, lease_ttl_seconds):
                # Another worker holds the lease; skip
                continue

            try:
                self.bus.publish(
                    run_id,
                    "WORKER_V2_TICK_REQUESTED",
                    {"run_id": run_id, "owner_id": owner_id, "env": env, "lane": lane},
                )
                self.ticker.tick_run(run_id)
                self.leases.renew(run_id, owner_id, lease_ttl_seconds)
                runs_ticked += 1
                ticks_used += 1
            finally:
                self.leases.release(run_id, owner_id)

        return WorkerTickSummary(
            owner_id=owner_id,
            env=env,
            lane=lane,
            ticks_used=ticks_used,
            runs_ticked=runs_ticked,
        )
