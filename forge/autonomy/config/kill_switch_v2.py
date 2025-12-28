from __future__ import annotations

from typing import Any, Dict


class KillSwitchV2:
    """
    Minimal kill switch object for Phase D.3.

    Shape of blob (stored in config_versions.kind == "kill_switch_v2"):
      { "lanes": { "env:lane": bool } }

    Default: everything enabled (no entries).
    """

    def __init__(self, blob: Dict[str, Any]):
        self.blob = blob or {}

    def lane_enabled(self, env: str, lane: str) -> bool:
        lanes = self.blob.get("lanes") or {}
        key = f"{env}:{lane}"
        # default allow if not specified
        return lanes.get(key, True)


class KillSwitchRegistry:
    """
    Registry wrapper that ensures a default allow-all kill switch exists.
    """

    def __init__(self, config_registry: Any):
        self.cfg = config_registry
        # Ensure a default record exists, but do not overwrite if one is already present.
        self.cfg.ensure_default("kill_switch_v2", {"lanes": {}}, created_by="system")

    def get_active(self) -> KillSwitchV2:
        blob = self.cfg.get_active("kill_switch_v2") or {"lanes": {}}
        return KillSwitchV2(blob)
