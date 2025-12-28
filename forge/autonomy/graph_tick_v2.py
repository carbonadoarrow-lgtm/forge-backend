from __future__ import annotations

from typing import Any, Dict, Optional


def _now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class GraphTickV2:
    """
    Minimal deterministic graph ticker for Phase D.3.

    Contract:
    - Supports only kind=="noop" steps.
    - One logical step per tick_run call.
    - Uses RunStoreV2.get_run_state_v2 / put_run_state_v2.
    - Emits events via EventBusV2.publish.
    - Optionally consults policy_loader.dispatch_allowed(state, step).
    """

    def __init__(self, store: Any, bus: Any, policy_loader: Any, artifact_writer: Any):
        self.store = store
        self.bus = bus
        self.policy_loader = policy_loader
        self.artifact_writer = artifact_writer

    def tick_run(self, run_id: str) -> Dict[str, Any]:
        state = self.store.get_run_state_v2(run_id)

        status = (state.get("status") or "").lower()
        if status in ("succeeded", "failed", "blocked", "canceled"):
            # Already terminal
            return state

        if state.get("started_at") is None:
            state["started_at"] = _now()
            state["status"] = "running"
            self.bus.publish(run_id, "RUN_STARTED", {"run_id": run_id})

        graph: Dict[str, Any] = state.get("run_graph") or {}
        steps: Dict[str, Any] = graph.get("steps") or {}

        next_step_id = _select_next_step_id(state, graph)
        if not next_step_id:
            # No remaining runnable steps → mark succeeded
            if state.get("status") == "running":
                state["status"] = "succeeded"
                state["finished_at"] = _now()
                self.bus.publish(run_id, "RUN_SUCCEEDED", {"run_id": run_id})
                self.store.put_run_state_v2(run_id, state)
            return state

        step = steps[next_step_id]
        kind = (step.get("kind") or "noop").lower()

        # Optional policy hook
        if hasattr(self.policy_loader, "dispatch_allowed"):
            ok, reason = self.policy_loader.dispatch_allowed(state, step)
            if not ok:
                state["status"] = "blocked"
                state["last_error"] = {"stage": "dispatch", "reason": reason}
                self.bus.publish(
                    run_id,
                    "RUN_BLOCKED",
                    {"run_id": run_id, "reason": reason, "step_id": next_step_id},
                )
                self.store.put_run_state_v2(run_id, state)
                return state

        self.bus.publish(run_id, "STEP_STARTED", {"run_id": run_id, "step_id": next_step_id})

        if kind == "noop":
            _mark_step(state, next_step_id, "succeeded")
            self.bus.publish(
                run_id,
                "STEP_SUCCEEDED",
                {"run_id": run_id, "step_id": next_step_id},
            )
        else:
            # Unsupported kind for Phase D.3 proof
            _mark_step(state, next_step_id, "failed")
            state["status"] = "failed"
            state["finished_at"] = _now()
            state["last_error"] = {
                "stage": "step",
                "reason": f"unsupported_kind:{kind}",
                "step_id": next_step_id,
            }
            self.bus.publish(
                run_id,
                "STEP_FAILED",
                {
                    "run_id": run_id,
                    "step_id": next_step_id,
                    "reason": f"unsupported_kind:{kind}",
                },
            )
            self.store.put_run_state_v2(run_id, state)
            return state

        # If all steps are now complete and still running, mark succeeded
        if _select_next_step_id(state, graph) is None and state.get("status") == "running":
            state["status"] = "succeeded"
            state["finished_at"] = _now()
            self.bus.publish(run_id, "RUN_SUCCEEDED", {"run_id": run_id})

        self.store.put_run_state_v2(run_id, state)
        return state


def _select_next_step_id(state: Dict[str, Any], graph: Dict[str, Any]) -> Optional[str]:
    steps: Dict[str, Any] = graph.get("steps") or {}
    entry = graph.get("entry_step")
    step_states: Dict[str, Any] = state.get("step_states") or {}

    ordered = []
    if entry and entry in steps:
        ordered.append(entry)
    for k in sorted(steps.keys()):
        if k not in ordered:
            ordered.append(k)

    for step_id in ordered:
        if step_states.get(step_id, {}).get("status") == "succeeded":
            continue
        deps = steps[step_id].get("deps") or []
        if all(step_states.get(d, {}).get("status") == "succeeded" for d in deps):
            return step_id
    return None


def _mark_step(state: Dict[str, Any], step_id: str, status: str) -> None:
    ss = state.setdefault("step_states", {})
    ss[step_id] = {"status": status, "updated_at": _now()}
