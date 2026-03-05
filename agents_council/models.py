"""Pydantic models for agent configuration."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class OutputConstraints(BaseModel):
    """Output constraints for an agent."""

    max_tokens: int = 500
    format_required: bool = True
    return_format: Optional[str] = None
    language: Optional[str] = None


class CollationRules(BaseModel):
    """Rules for collating multi-agent outputs."""

    top_actions_limit: int = 5
    deduplicate_by_lemma: bool = True
    time_block_format: Optional[str] = None


class ConvenorConfig(BaseModel):
    """Configuration for the convenor/orchestrator agent."""

    agent_order: List[str] = Field(default_factory=list)
    parallel: bool = True
    max_wait_seconds: int = 30
    collation_rules: CollationRules = Field(default_factory=CollationRules)
    data_sources: Dict[str, str] = Field(default_factory=dict)


class AgentMode(BaseModel):
    """Configuration for a single agent mode."""

    id: str
    name: str
    description: str
    default_model: str = "cursor-default-large"
    worktree_enabled: bool = False
    allowed_tools: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    system_prompt: str
    output_constraints: OutputConstraints = Field(default_factory=OutputConstraints)
    convenor_config: Optional[ConvenorConfig] = None


class ModesConfig(BaseModel):
    """Root configuration containing all agent modes."""

    modes: List[AgentMode]
    personal_modes: List[AgentMode] = Field(default_factory=list)

    @property
    def all_modes(self) -> List[AgentMode]:
        return self.modes + self.personal_modes

    def get_mode(self, mode_id: str) -> Optional[AgentMode]:
        """Get a mode by its ID (searches both pro and personal)."""
        for mode in self.all_modes:
            if mode.id == mode_id:
                return mode
        return None

    def list_mode_ids(self) -> List[str]:
        """List all available mode IDs."""
        return [mode.id for mode in self.all_modes]


class AgentInvocation(BaseModel):
    """Request to invoke an agent."""

    mode_id: str
    user_request: str
    context: Dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from an agent invocation."""

    mode_id: str
    agent_name: str
    output: str
    format_valid: bool = True
    error: Optional[str] = None


class CouncilReport(BaseModel):
    """Final collated report from the council convenor."""

    convenor_summary: str
    senior_em: Optional[AgentResponse] = None
    pr_reviewer: Optional[AgentResponse] = None
    career_coach: Optional[AgentResponse] = None
    top_actions: List[str] = Field(default_factory=list)
    info_required: List[str] = Field(default_factory=list)
