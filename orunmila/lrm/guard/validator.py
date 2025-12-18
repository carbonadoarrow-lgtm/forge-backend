"""
Communication Guard - Taylor mode compliance validator.

Enforces hardened communication rules for critical operations.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class TaylorViolation:
    """
    Record of a Taylor mode violation.

    violation_type: Type of violation (e.g., "missing_slot", "forbidden_phrase")
    message: Description of violation
    context: Optional context (e.g., which slot is missing)
    """
    violation_type: str
    message: str
    context: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "violation_type": self.violation_type,
            "message": self.message,
            "context": self.context,
        }


class CommunicationGuard:
    """
    Validates LLM responses for Taylor mode compliance.

    Taylor mode requirements:
    1. Must use 5-slot structure:
       - observation (what happened)
       - implication (what it means)
       - constraints (what limits response)
       - choice_set (available actions)
       - meta_clarifier (context/nuance)

    2. Forbidden phrases:
       - "I understand" / "I see"
       - Claims of emotion or consciousness
       - Overly apologetic language
       - Ungrounded certainty claims

    3. Must be factual and grounded
    """

    # Forbidden phrases that indicate non-Taylor compliance
    FORBIDDEN_PHRASES = [
        r"\bI understand\b",
        r"\bI see\b",
        r"\bI feel\b",
        r"\bI believe\b",
        r"\bI'm sorry\b",
        r"\bApologies\b",
        r"\bMy apologies\b",
        r"\bI'm confident\b",
        r"\bI'm certain\b",
        r"\bI fully understand\b",
        r"\bI completely understand\b",
    ]

    # Required slots in Taylor structure
    REQUIRED_SLOTS = [
        "observation",
        "implication",
        "constraints",
        "choice_set",
        "meta_clarifier",
    ]

    def __init__(self, strict_mode: bool = False):
        """
        Initialize communication guard.

        Args:
            strict_mode: If True, require all 5 slots. If False, allow partial structures.
        """
        self.strict_mode = strict_mode
        logger.debug(f"CommunicationGuard initialized (strict_mode={strict_mode})")

    def validate_message(self, message: str) -> List[TaylorViolation]:
        """
        Validate a message for Taylor compliance.

        Args:
            message: Message to validate

        Returns:
            List of violations (empty if compliant)
        """
        violations = []

        # Check for forbidden phrases
        for pattern in self.FORBIDDEN_PHRASES:
            if re.search(pattern, message, re.IGNORECASE):
                violations.append(TaylorViolation(
                    violation_type="forbidden_phrase",
                    message=f"Forbidden phrase detected: {pattern}",
                    context=message[:100],
                ))

        return violations

    def validate_structure(self, response_dict: Dict[str, Any]) -> List[TaylorViolation]:
        """
        Validate a structured response for Taylor compliance.

        Args:
            response_dict: Dictionary with Taylor slots

        Returns:
            List of violations (empty if compliant)
        """
        violations = []

        # Check for required slots
        for slot in self.REQUIRED_SLOTS:
            if slot not in response_dict:
                violations.append(TaylorViolation(
                    violation_type="missing_slot",
                    message=f"Required slot missing: {slot}",
                    context=slot,
                ))
            elif not response_dict[slot]:
                violations.append(TaylorViolation(
                    violation_type="empty_slot",
                    message=f"Slot is empty: {slot}",
                    context=slot,
                ))

        # Check constraints slot (should be a list)
        if "constraints" in response_dict and not isinstance(response_dict["constraints"], list):
            violations.append(TaylorViolation(
                violation_type="invalid_type",
                message="constraints must be a list",
                context="constraints",
            ))

        # Check choice_set slot (should be a list)
        if "choice_set" in response_dict and not isinstance(response_dict["choice_set"], list):
            violations.append(TaylorViolation(
                violation_type="invalid_type",
                message="choice_set must be a list",
                context="choice_set",
            ))

        # Check for forbidden phrases in all slots
        for slot, value in response_dict.items():
            if isinstance(value, str):
                slot_violations = self.validate_message(value)
                for v in slot_violations:
                    v.context = f"{slot}: {v.context}"
                    violations.extend(slot_violations)

        return violations

    def is_compliant(self, message: str) -> bool:
        """
        Check if message is Taylor compliant.

        Args:
            message: Message to check

        Returns:
            True if compliant (no violations)
        """
        violations = self.validate_message(message)
        return len(violations) == 0

    def block_if_violated(self, message: str, event_emitter=None) -> bool:
        """
        Block message if it violates Taylor mode.

        Args:
            message: Message to check
            event_emitter: Optional EventEmitter to emit violation events

        Returns:
            True if blocked (violations found), False if allowed
        """
        violations = self.validate_message(message)

        if violations:
            logger.warning(f"Taylor mode violation detected: {len(violations)} violations")

            # Emit event
            if event_emitter:
                violation_messages = [v.message for v in violations]
                event_emitter.emit_taylor_violation(message[:200], violation_messages)

            return True  # Block

        return False  # Allow

    def get_violation_summary(self, violations: List[TaylorViolation]) -> str:
        """
        Get human-readable summary of violations.

        Args:
            violations: List of violations

        Returns:
            Summary string
        """
        if not violations:
            return "No violations"

        summary = f"{len(violations)} violation(s):\n"
        for i, v in enumerate(violations, 1):
            summary += f"{i}. {v.violation_type}: {v.message}\n"

        return summary
