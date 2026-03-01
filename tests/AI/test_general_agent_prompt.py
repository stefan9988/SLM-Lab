"""Tests for build_general_agent_prompt() and get_delegatable_agents()."""

import pytest

from AI.agents.metadata import AgentMetadata, get_delegatable_agents
from AI.prompts.general_agent_prompt import (
    GENERAL_AGENT_PROMPT,
    build_general_agent_prompt,
)

# ---------------------------------------------------------------------------
# get_delegatable_agents
# ---------------------------------------------------------------------------


def test_get_delegatable_agents_returns_list():
    result = get_delegatable_agents()
    assert isinstance(result, list)


def test_get_delegatable_agents_includes_validation_agent():
    names = [a.name for a in get_delegatable_agents()]
    assert "validation_agent" in names


def test_get_delegatable_agents_only_delegatable():
    for agent in get_delegatable_agents():
        assert agent.delegatable is True


# ---------------------------------------------------------------------------
# build_general_agent_prompt — behavior rules always present
# ---------------------------------------------------------------------------


def test_behavior_rules_always_present_with_no_agents():
    prompt = build_general_agent_prompt()
    assert "Behavior rules" in prompt


def test_behavior_rules_always_present_with_agents():
    agent = AgentMetadata(
        name="test_agent",
        display_name="Test Agent",
        description="Does things.",
        delegatable=True,
    )
    prompt = build_general_agent_prompt([agent])
    assert "Behavior rules" in prompt


# ---------------------------------------------------------------------------
# build_general_agent_prompt — empty / None → no delegation section
# ---------------------------------------------------------------------------


def test_no_delegation_section_when_no_agents():
    prompt = build_general_agent_prompt()
    assert "Delegation" not in prompt


def test_no_delegation_section_when_none():
    prompt = build_general_agent_prompt(None)
    assert "Delegation" not in prompt


def test_no_delegation_section_when_empty_list():
    prompt = build_general_agent_prompt([])
    assert "Delegation" not in prompt


# ---------------------------------------------------------------------------
# build_general_agent_prompt — single agent appears correctly
# ---------------------------------------------------------------------------


def test_single_agent_display_name_in_prompt():
    agent = AgentMetadata(
        name="my_agent",
        display_name="My Agent",
        description="Checks things.",
        delegatable=True,
    )
    prompt = build_general_agent_prompt([agent])
    assert "My Agent" in prompt


def test_single_agent_description_in_prompt():
    agent = AgentMetadata(
        name="my_agent",
        display_name="My Agent",
        description="Checks things.",
        delegatable=True,
    )
    prompt = build_general_agent_prompt([agent])
    assert "Checks things." in prompt


def test_single_agent_delegation_section_present():
    agent = AgentMetadata(
        name="my_agent",
        display_name="My Agent",
        description="Checks things.",
        delegatable=True,
    )
    prompt = build_general_agent_prompt([agent])
    assert "Delegation" in prompt


# ---------------------------------------------------------------------------
# build_general_agent_prompt — multiple agents all appear, in order
# ---------------------------------------------------------------------------


def test_multiple_agents_all_appear():
    agents = [
        AgentMetadata(
            name="agent_a",
            display_name="Agent A",
            description="Does A.",
            delegatable=True,
        ),
        AgentMetadata(
            name="agent_b",
            display_name="Agent B",
            description="Does B.",
            delegatable=True,
        ),
    ]
    prompt = build_general_agent_prompt(agents)
    assert "Agent A" in prompt
    assert "Agent B" in prompt
    assert "Does A." in prompt
    assert "Does B." in prompt


def test_multiple_agents_appear_in_order():
    agents = [
        AgentMetadata(
            name="agent_a",
            display_name="Agent A",
            description="Does A.",
            delegatable=True,
        ),
        AgentMetadata(
            name="agent_b",
            display_name="Agent B",
            description="Does B.",
            delegatable=True,
        ),
    ]
    prompt = build_general_agent_prompt(agents)
    assert prompt.index("Agent A") < prompt.index("Agent B")


# ---------------------------------------------------------------------------
# GENERAL_AGENT_PROMPT backward-compat constant
# ---------------------------------------------------------------------------


def test_general_agent_prompt_constant_is_non_empty():
    assert isinstance(GENERAL_AGENT_PROMPT, str)
    assert len(GENERAL_AGENT_PROMPT) > 0


def test_general_agent_prompt_constant_has_no_delegation_section():
    # The module-level constant is built with no agents, so no delegation section.
    assert "Delegation" not in GENERAL_AGENT_PROMPT


def test_general_agent_prompt_constant_has_behavior_rules():
    assert "Behavior rules" in GENERAL_AGENT_PROMPT


# ---------------------------------------------------------------------------
# get_delegatable_agents — document_agent is included
# ---------------------------------------------------------------------------


def test_get_delegatable_agents_includes_document_agent():
    names = [a.name for a in get_delegatable_agents()]
    assert "document_agent" in names


def test_document_agent_display_name_in_prompt():
    prompt = build_general_agent_prompt(get_delegatable_agents())
    assert "Document Agent" in prompt


def test_document_agent_description_in_prompt():
    prompt = build_general_agent_prompt(get_delegatable_agents())
    assert "structured data extracted from a document" in prompt
