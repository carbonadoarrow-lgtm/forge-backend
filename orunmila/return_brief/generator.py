"""
Return Brief Generator - Create comprehensive status reports.

Generates briefings covering:
- Presence status
- Recent events
- Applied neuroplasticity intents
- Corridor status
- Recommendations
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import json
import logging

logger = logging.getLogger(__name__)


class ReturnBriefGenerator:
    """
    Generates return briefs for founder after extended absence.

    - Consolidates status from all Orunmila subsystems
    - Formats as readable markdown
    - Saves to timestamped files
    """

    def __init__(
        self,
        output_dir: str = "data/orunmila/return_briefs",
        presence_state_machine=None,
        event_emitter=None,
        corridor_manager=None,
        neuroplasticity_applicator=None,
    ):
        """
        Initialize return brief generator.

        Args:
            output_dir: Directory to save briefs
            presence_state_machine: PresenceStateMachine instance
            event_emitter: EventEmitter instance
            corridor_manager: CorridorManager instance
            neuroplasticity_applicator: IntentApplicator instance
        """
        self.output_dir = Path(output_dir)
        self.presence_state_machine = presence_state_machine
        self.event_emitter = event_emitter
        self.corridor_manager = corridor_manager
        self.neuroplasticity_applicator = neuroplasticity_applicator

        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("ReturnBriefGenerator initialized")

    def generate_brief(self) -> str:
        """
        Generate return brief.

        Returns:
            Path to generated brief file
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        brief_path = self.output_dir / f"return_brief_{timestamp}.md"

        sections = []

        # Header
        sections.append(self._generate_header())

        # Presence status
        if self.presence_state_machine:
            sections.append(self._generate_presence_section())

        # Recent events
        if self.event_emitter:
            sections.append(self._generate_events_section())

        # Corridor status
        if self.corridor_manager:
            sections.append(self._generate_corridors_section())

        # Applied intents
        if self.neuroplasticity_applicator:
            sections.append(self._generate_neuroplasticity_section())

        # Recommendations
        sections.append(self._generate_recommendations())

        # Footer
        sections.append(self._generate_footer())

        # Write to file
        brief_content = "\n\n---\n\n".join(sections)
        brief_path.write_text(brief_content, encoding="utf-8")

        logger.info(f"Generated return brief: {brief_path}")
        return str(brief_path)

    def _generate_header(self) -> str:
        """Generate header section."""
        now = datetime.utcnow().isoformat()
        return f"""# Orunmila Return Brief

**Generated:** {now}

Welcome back! This brief summarizes system activity during your absence.
"""

    def _generate_presence_section(self) -> str:
        """Generate presence status section."""
        status = self.presence_state_machine.get_status()

        section = "## Presence Status\n\n"
        section += f"**Current State:** {status.state.value.upper()}\n"
        section += f"**Last Activity:** {status.last_activity.timestamp}\n"
        section += f"**Activity Type:** {status.last_activity.activity_type}\n"
        section += f"**Business Hours Elapsed:** {status.hours_since_last:.1f} hours\n"

        if status.state.value != "normal":
            section += f"\n⚠️ **Note:** System was in {status.state.value.upper()} state.\n"

        return section

    def _generate_events_section(self) -> str:
        """Generate recent events section."""
        recent_events = self.event_emitter.get_recent_events(limit=20)

        section = "## Recent Events\n\n"

        if not recent_events:
            section += "_No events recorded._\n"
            return section

        # Group by severity
        by_severity = {}
        for event in recent_events:
            severity = event.severity.value
            if severity not in by_severity:
                by_severity[severity] = []
            by_severity[severity].append(event)

        section += f"**Total Events:** {len(recent_events)}\n\n"

        for severity in ["critical", "error", "warn", "info", "debug"]:
            if severity in by_severity:
                count = len(by_severity[severity])
                section += f"- **{severity.upper()}:** {count} event(s)\n"

        section += "\n### Notable Events\n\n"

        # Show critical/error events
        for event in recent_events:
            if event.severity.value in ["critical", "error"]:
                section += f"- **{event.event_type}** ({event.severity.value})\n"
                section += f"  - {event.taylor_summary.observation}\n"

        return section

    def _generate_corridors_section(self) -> str:
        """Generate corridor status section."""
        status = self.corridor_manager.get_current_status()

        section = "## Corridor Status\n\n"
        section += f"**Current Level:** {status.level.value.upper()}\n"
        section += f"**Configuration:**\n"
        section += f"- Max Parallel Tasks: {status.config.max_parallel_tasks}\n"
        section += f"- Token Budget: {status.config.token_budget}\n"
        section += f"- Max Tool Calls: {status.config.max_tool_calls}\n"
        section += f"- Requires Approval: {status.config.require_approval}\n"
        section += f"- Taylor Mode Strict: {status.config.taylor_mode_strict}\n"

        return section

    def _generate_neuroplasticity_section(self) -> str:
        """Generate neuroplasticity section."""
        applied_intents = self.neuroplasticity_applicator.read_applied_intents()

        section = "## Neuroplasticity Updates\n\n"

        if not applied_intents:
            section += "_No intents applied during absence._\n"
            return section

        section += f"**Applied Intents:** {len(applied_intents)}\n\n"

        for intent in applied_intents[-5:]:  # Last 5
            section += f"- **{intent.description}**\n"
            section += f"  - Confidence: {intent.confidence:.2f}\n"
            section += f"  - Applied: {intent.timestamp}\n"

        return section

    def _generate_recommendations(self) -> str:
        """Generate recommendations section."""
        section = "## Recommendations\n\n"

        recommendations = []

        # Check presence state
        if self.presence_state_machine:
            status = self.presence_state_machine.get_status()
            if status.state.value == "takeover":
                recommendations.append("Review all actions taken during TAKEOVER state")
                recommendations.append("Consider adjusting presence thresholds if false alarm")

        # Check events
        if self.event_emitter:
            recent_events = self.event_emitter.get_recent_events(limit=100)
            error_count = len([e for e in recent_events if e.severity.value in ["error", "critical"]])
            if error_count > 5:
                recommendations.append(f"Investigate {error_count} error/critical events")

        # Check applied intents
        if self.neuroplasticity_applicator:
            applied = self.neuroplasticity_applicator.read_applied_intents()
            if applied:
                recommendations.append(f"Review {len(applied)} auto-applied configuration changes")

        if not recommendations:
            section += "_No urgent actions required._\n"
        else:
            for i, rec in enumerate(recommendations, 1):
                section += f"{i}. {rec}\n"

        return section

    def _generate_footer(self) -> str:
        """Generate footer section."""
        return """---

**Orunmila v0.1**

This brief was automatically generated by the Orunmila Events System.
"""

    def generate_json_brief(self) -> Dict[str, Any]:
        """
        Generate return brief as JSON.

        Returns:
            Brief data as dictionary
        """
        brief_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "version": "0.1.0",
        }

        if self.presence_state_machine:
            status = self.presence_state_machine.get_status()
            brief_data["presence"] = status.to_dict()

        if self.event_emitter:
            recent_events = self.event_emitter.get_recent_events(limit=20)
            brief_data["events"] = {
                "total": len(recent_events),
                "recent": [e.to_dict() for e in recent_events[:5]],
            }

        if self.corridor_manager:
            status = self.corridor_manager.get_current_status()
            brief_data["corridors"] = status.to_dict()

        if self.neuroplasticity_applicator:
            applied = self.neuroplasticity_applicator.read_applied_intents()
            brief_data["neuroplasticity"] = {
                "applied_count": len(applied),
                "recent": [i.to_dict() for i in applied[-5:]],
            }

        return brief_data
