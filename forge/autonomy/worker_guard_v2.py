import os
import threading
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class WorkerGuardStatus:
    enabled: bool
    reason: str
    pid: int
    configured_pid: int

_LOCK = threading.Lock()
_STARTED = False

def can_start_worker(enabled: bool, configured_pid: int) -> WorkerGuardStatus:
    pid = os.getpid()
    if not enabled:
        return WorkerGuardStatus(False, "AUTONOMY_V2_WORKER_ENABLED=false", pid, configured_pid)
    if configured_pid and pid != configured_pid:
        return WorkerGuardStatus(False, f"pid_mismatch (pid={pid} expected={configured_pid})", pid, configured_pid)
    return WorkerGuardStatus(True, "ok", pid, configured_pid)

def mark_started_once() -> bool:
    """
    Returns True only the first time per-process.
    Prevents double-start inside one process (e.g. reload quirks).
    """
    global _STARTED
    with _LOCK:
        if _STARTED:
            return False
        _STARTED = True
        return True
