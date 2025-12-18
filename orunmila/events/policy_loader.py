"""
Policy Loader - Load routing policies from configuration files.

Supports YAML/JSON policy files for flexible event routing configuration.
"""

from pathlib import Path
from typing import Dict, Any, List
import logging
import json

from .router import EventRouter, RoutingRule
from .contracts import Severity

logger = logging.getLogger(__name__)


def load_policy_from_file(router: EventRouter, policy_path: str):
    """
    Load routing policy from YAML/JSON file.

    Expected format:
    {
        "rules": [
            {
                "channel": "telegram",
                "event_types": ["presence.warn_threshold"],
                "min_severity": "warn"
            },
            ...
        ]
    }

    Args:
        router: EventRouter instance to load rules into
        policy_path: Path to policy file
    """
    path = Path(policy_path)
    if not path.exists():
        logger.warning(f"Policy file not found: {policy_path}")
        return

    try:
        # Load file
        with open(path, "r", encoding="utf-8") as f:
            if path.suffix == ".json":
                data = json.load(f)
            elif path.suffix in [".yaml", ".yml"]:
                try:
                    import yaml
                    data = yaml.safe_load(f)
                except ImportError:
                    logger.error("PyYAML not installed. Install with: pip install pyyaml")
                    return
            else:
                logger.error(f"Unsupported policy file format: {path.suffix}")
                return

        # Parse rules
        rules = data.get("rules", [])
        for rule_data in rules:
            rule = parse_routing_rule(rule_data)
            if rule:
                router.add_rule(rule)

        logger.info(f"Loaded {len(rules)} routing rules from {policy_path}")

    except Exception as e:
        logger.error(f"Failed to load policy from {policy_path}: {e}")


def parse_routing_rule(rule_data: Dict[str, Any]) -> RoutingRule:
    """
    Parse routing rule from dictionary.

    Args:
        rule_data: Rule data dictionary

    Returns:
        RoutingRule instance
    """
    try:
        channel = rule_data["channel"]
        event_types = rule_data.get("event_types", None)
        min_severity_str = rule_data.get("min_severity", "info")
        min_severity = Severity(min_severity_str.lower())

        return RoutingRule(
            channel=channel,
            event_types=event_types,
            min_severity=min_severity,
        )
    except Exception as e:
        logger.error(f"Failed to parse routing rule: {e}")
        return None


def save_policy_to_file(router: EventRouter, policy_path: str):
    """
    Save routing policy to JSON file.

    Args:
        router: EventRouter instance
        policy_path: Path to save policy file
    """
    path = Path(policy_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        rules_data = []
        for rule in router.rules:
            rules_data.append({
                "channel": rule.channel,
                "event_types": rule.event_types,
                "min_severity": rule.min_severity.value,
            })

        data = {"rules": rules_data}

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(rules_data)} routing rules to {policy_path}")

    except Exception as e:
        logger.error(f"Failed to save policy to {policy_path}: {e}")
