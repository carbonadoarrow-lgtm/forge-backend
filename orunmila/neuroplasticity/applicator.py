"""
Intent Applicator - Apply intents to configuration files.

Safely applies approved intents to leto_mindset.yaml and other configs.
"""

from pathlib import Path
from typing import Dict, Any, List
import json
import logging

from .contracts import Intent, IntentStatus

logger = logging.getLogger(__name__)


class IntentApplicator:
    """
    Applies intents to configuration files.

    - Validates intents before application
    - Creates backups before modification
    - Logs all applications for rollback
    """

    def __init__(
        self,
        intents_log_path: str = "data/orunmila/intents.jsonl",
        event_emitter=None,
    ):
        """
        Initialize intent applicator.

        Args:
            intents_log_path: Path to intents log file
            event_emitter: Optional EventEmitter for emitting neuroplasticity events
        """
        self.intents_log_path = Path(intents_log_path)
        self.event_emitter = event_emitter

        self._ensure_log_exists()
        logger.info("IntentApplicator initialized")

    def _ensure_log_exists(self):
        """Create intents log if it doesn't exist."""
        self.intents_log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.intents_log_path.exists():
            self.intents_log_path.touch()

    def apply_intent(self, intent: Intent, config_path: str) -> bool:
        """
        Apply intent to configuration file.

        Args:
            intent: Intent to apply
            config_path: Path to config file

        Returns:
            True if applied successfully, False otherwise
        """
        # Validate intent
        if intent.status != IntentStatus.APPROVED:
            logger.warning(f"Intent {intent.intent_id} not approved, skipping")
            return False

        if not intent.config_patch:
            logger.warning(f"Intent {intent.intent_id} has no config patch, skipping")
            return False

        # Create backup
        backup_path = self._create_backup(config_path)
        if not backup_path:
            logger.error(f"Failed to create backup for {config_path}")
            return False

        try:
            # Apply patch
            self._apply_patch(config_path, intent.config_patch)

            # Mark intent as applied
            intent.status = IntentStatus.APPLIED
            self._log_intent(intent)

            # Emit event
            if self.event_emitter:
                self.event_emitter.emit_neuroplasticity_update(
                    intent=intent.description,
                    applied=True,
                    reason="Auto-applied from clear intent",
                )

            logger.info(f"Applied intent {intent.intent_id} to {config_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply intent {intent.intent_id}: {e}")

            # Restore backup
            self._restore_backup(config_path, backup_path)

            # Emit event
            if self.event_emitter:
                self.event_emitter.emit_neuroplasticity_update(
                    intent=intent.description,
                    applied=False,
                    reason=f"Application failed: {str(e)}",
                )

            return False

    def _create_backup(self, config_path: str) -> Path:
        """
        Create backup of config file.

        Args:
            config_path: Path to config file

        Returns:
            Path to backup file
        """
        try:
            path = Path(config_path)
            if not path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return None

            backup_path = path.parent / f"{path.stem}.backup{path.suffix}"
            backup_path.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")

            logger.debug(f"Created backup: {backup_path}")
            return backup_path

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None

    def _restore_backup(self, config_path: str, backup_path: Path):
        """
        Restore config from backup.

        Args:
            config_path: Path to config file
            backup_path: Path to backup file
        """
        try:
            path = Path(config_path)
            path.write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
            logger.info(f"Restored config from backup: {backup_path}")
        except Exception as e:
            logger.error(f"Failed to restore backup: {e}")

    def _apply_patch(self, config_path: str, patch: Dict[str, Any]):
        """
        Apply patch to config file.

        Args:
            config_path: Path to config file
            patch: Patch to apply
        """
        path = Path(config_path)

        # For JSON files
        if path.suffix == ".json":
            with open(path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Apply patch (simple merge)
            self._merge_dict(config, patch)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

        # For YAML files
        elif path.suffix in [".yaml", ".yml"]:
            try:
                import yaml

                with open(path, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)

                # Apply patch (simple merge)
                self._merge_dict(config, patch)

                with open(path, "w", encoding="utf-8") as f:
                    yaml.dump(config, f, default_flow_style=False)

            except ImportError:
                logger.error("PyYAML not installed. Install with: pip install pyyaml")
                raise

        else:
            logger.error(f"Unsupported config format: {path.suffix}")
            raise ValueError(f"Unsupported config format: {path.suffix}")

    def _merge_dict(self, target: Dict[str, Any], patch: Dict[str, Any]):
        """
        Recursively merge patch into target.

        Args:
            target: Target dictionary (modified in place)
            patch: Patch dictionary
        """
        for key, value in patch.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._merge_dict(target[key], value)
            else:
                target[key] = value

    def _log_intent(self, intent: Intent):
        """
        Log applied intent.

        Args:
            intent: Intent to log
        """
        try:
            with open(self.intents_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(intent.to_dict()) + "\n")
            logger.debug(f"Logged intent {intent.intent_id}")
        except Exception as e:
            logger.error(f"Failed to log intent: {e}")

    def read_applied_intents(self) -> List[Intent]:
        """
        Read all applied intents.

        Returns:
            List of applied intents
        """
        intents = []
        try:
            with open(self.intents_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            intent = Intent.from_dict(json.loads(line))
                            if intent.status == IntentStatus.APPLIED:
                                intents.append(intent)
                        except Exception as e:
                            logger.warning(f"Failed to parse intent line: {e}")
        except FileNotFoundError:
            logger.warning(f"Intents log not found: {self.intents_log_path}")
        except Exception as e:
            logger.error(f"Failed to read intents: {e}")

        return intents
