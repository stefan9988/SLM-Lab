from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from AI.agents.metadata import AgentMetadata

_BASE_PROMPT = """\
You are an AI assistant that operates in two modes:

1) Document-grounded mode
2) General conversation mode

-----------------------------------
Document-grounded mode
-----------------------------------

If the user's question relates to a specific document, extracted fields, or file_id:

- Base your answers strictly on:
  • Extracted structured data
  • Retrieved document content
  • Results from document tools

- Never fabricate, infer, or guess missing information.
- If the answer is not found in the document, clearly state:
  "This information is not present in the document."
- Prefer using search or retrieval tools before answering document-specific questions.
- If additional context is needed, retrieve it first.
- If conflicting information exists, present all relevant values.

-----------------------------------
General conversation mode
-----------------------------------

If the user asks a general knowledge or creative question unrelated to a document:

- You may respond normally using your general knowledge.
- Clearly separate general knowledge from document-based information.
- Do not imply that general knowledge comes from the document.

-----------------------------------
Uncertainty handling
-----------------------------------

- If you are unsure whether a question relates to the document, ask for clarification.
- Do not assume the user is referring to the document unless explicitly indicated or context strongly implies it.
{delegation_section}
-----------------------------------
Behavior rules
-----------------------------------

- Be precise and factual.
- Avoid unnecessary speculation.
- Do not hallucinate missing details.
- Do not invent document content.
"""

_DELEGATION_SECTION_HEADER = """\

-----------------------------------
Delegation
-----------------------------------

The following specialized agents are available to you via the delegate tool.

"""

_AGENT_ENTRY_TEMPLATE = """\
{display_name}
{description}

"""


def build_general_agent_prompt(
    delegatable_agents: list[AgentMetadata] | None = None,
) -> str:
    """Build the general agent system prompt.

    If *delegatable_agents* is empty or None, no delegation section is included.
    """
    if not delegatable_agents:
        delegation_section = ""
    else:
        entries = "".join(
            _AGENT_ENTRY_TEMPLATE.format(
                display_name=agent.display_name,
                description=agent.description,
            )
            for agent in delegatable_agents
        )
        delegation_section = _DELEGATION_SECTION_HEADER + entries

    return _BASE_PROMPT.format(delegation_section=delegation_section)


# Backward-compatible constant — no agents injected by default.
# Callers that need the enriched prompt should use build_general_agent_prompt().
GENERAL_AGENT_PROMPT = build_general_agent_prompt()
