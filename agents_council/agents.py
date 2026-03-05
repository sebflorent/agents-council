"""Agent registry and execution logic."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional

from .models import AgentInvocation, AgentMode, AgentResponse, CouncilReport, ModesConfig


class AgentRegistry:
    """Registry for loading and managing agent modes."""

    def __init__(self, modes_path: Optional[Path] = None) -> None:
        self.modes_path = modes_path or Path("modes.json")
        self._config: Optional[ModesConfig] = None

    def load(self) -> ModesConfig:
        """Load modes configuration from file."""
        if self._config is not None:
            return self._config

        if not self.modes_path.exists():
            raise FileNotFoundError(f"Modes file not found: {self.modes_path}")

        with open(self.modes_path) as f:
            data = json.load(f)

        self._config = ModesConfig.model_validate(data)
        return self._config

    def get_mode(self, mode_id: str) -> Optional[AgentMode]:
        """Get a specific mode by ID."""
        config = self.load()
        return config.get_mode(mode_id)

    def list_modes(self) -> List[Dict[str, str]]:
        """List all available modes with basic info."""
        config = self.load()
        result = []
        for mode in config.modes:
            result.append({"id": mode.id, "name": mode.name, "description": mode.description, "category": "professional"})
        for mode in config.personal_modes:
            result.append({"id": mode.id, "name": mode.name, "description": mode.description, "category": "personal"})
        return result


class AgentExecutor:
    """Executes agent invocations using Cursor's built-in models.

    NOTE: This executor formats prompts for Cursor's chat interface.
    The actual LLM call happens through Cursor's native model routing.
    """

    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def build_prompt(self, mode: AgentMode, invocation: AgentInvocation) -> str:
        """Build the full prompt for an agent invocation."""
        # Start with system prompt
        prompt_parts = [
            f"# Agent: {mode.name}",
            "",
            "## System Instructions",
            mode.system_prompt.replace("\\n", "\n"),
            "",
            "## User Request",
            invocation.user_request,
        ]

        # Add context if provided
        if invocation.context:
            prompt_parts.extend([
                "",
                "## Context",
                json.dumps(invocation.context, indent=2),
            ])

        # Add output format reminder
        if mode.output_constraints.format_required:
            prompt_parts.extend([
                "",
                "## Output Requirements",
                f"- Maximum tokens: {mode.output_constraints.max_tokens}",
                "- Follow the exact output format specified in system instructions.",
            ])
            if mode.output_constraints.return_format == "json":
                prompt_parts.append("- Return valid JSON.")

        return "\n".join(prompt_parts)

    def validate_output_format(self, mode: AgentMode, output: str) -> bool:
        """Validate that output matches the expected format."""
        if not mode.output_constraints.format_required:
            return True

        # Check for JSON format if required
        if mode.output_constraints.return_format == "json":
            try:
                json.loads(output)
                return True
            except json.JSONDecodeError:
                return False

        # Check for expected section headers based on agent type
        format_patterns: Dict[str, List[str]] = {
            "senior_em_agent": [r"SUMMARY:", r"ACTIONS:", r"MILESTONES:"],
            "pr_reviewer_agent": [r"ONE-LINE VERDICT:", r"TOP RISKS:", r"ACTIONS:"],
            "career_coach_agent": [r"VISION:", r"SKILL_GAPS:", r"3_MONTH_PLAN:", r"METRICS:"],
        }

        patterns = format_patterns.get(mode.id, [])
        if not patterns:
            return True

        return all(re.search(pattern, output) for pattern in patterns)

    def format_for_cursor(self, mode: AgentMode, invocation: AgentInvocation) -> Dict:
        """Format invocation for Cursor's interface.

        Returns a dict that can be used with Cursor's chat/completion API.
        """
        return {
            "agent_id": mode.id,
            "agent_name": mode.name,
            "system_prompt": mode.system_prompt.replace("\\n", "\n"),
            "user_message": invocation.user_request,
            "context": invocation.context,
            "model": mode.default_model,
            "max_tokens": mode.output_constraints.max_tokens,
            "tools": mode.allowed_tools,
        }


class CouncilConvenor:
    """Orchestrator that dispatches to multiple agents and collates results."""

    def __init__(self, registry: AgentRegistry, executor: AgentExecutor) -> None:
        self.registry = registry
        self.executor = executor

    def prepare_dispatch(self, user_request: str, context: dict) -> List[Dict]:
        """Prepare invocations for all council agents.

        Returns a list of formatted prompts ready for Cursor's interface.
        """
        convenor_mode = self.registry.get_mode("council_convenor")
        if not convenor_mode or not convenor_mode.convenor_config:
            raise ValueError("Council convenor mode not found or misconfigured")

        dispatches = []
        for agent_id in convenor_mode.convenor_config.agent_order:
            mode = self.registry.get_mode(agent_id)
            if not mode:
                continue

            invocation = AgentInvocation(
                mode_id=agent_id,
                user_request=user_request,
                context=context,
            )

            dispatches.append({
                "agent_id": agent_id,
                "invocation": self.executor.format_for_cursor(mode, invocation),
                "prompt": self.executor.build_prompt(mode, invocation),
            })

        return dispatches

    def collate_responses(self, responses: List[AgentResponse]) -> CouncilReport:
        """Collate responses from all agents into a final report."""
        report = CouncilReport(convenor_summary="")

        actions: List[str] = []
        info_required: List[str] = []

        for response in responses:
            # Assign to correct slot
            if response.mode_id == "senior_em_agent":
                report.senior_em = response
            elif response.mode_id == "pr_reviewer_agent":
                report.pr_reviewer = response
            elif response.mode_id == "career_coach_agent":
                report.career_coach = response

            # Extract actions from output
            if "ACTIONS:" in response.output:
                action_section = response.output.split("ACTIONS:")[-1]
                action_lines = action_section.split("\n")
                for line in action_lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith("-")):
                        actions.append(f"[{response.agent_name}] {line}")

            # Check for info requests
            if "need more info" in response.output.lower() or "?" in response.output:
                for line in response.output.split("\n"):
                    if "?" in line:
                        info_required.append(f"[{response.agent_name}] {line.strip()}")

        # Deduplicate and limit actions
        seen: set = set()
        unique_actions: List[str] = []
        for action in actions:
            normalized = action.lower().strip()
            if normalized not in seen:
                seen.add(normalized)
                unique_actions.append(action)
                if len(unique_actions) >= 5:
                    break

        report.top_actions = unique_actions
        report.info_required = info_required

        # Generate summary
        agent_count = sum(1 for r in responses if not r.error)
        report.convenor_summary = (
            f"Council completed with {agent_count}/{len(responses)} agents responding. "
            f"Top {len(unique_actions)} actions extracted."
        )

        return report
