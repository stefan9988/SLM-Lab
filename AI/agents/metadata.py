"""Static metadata for agents used at prompt-construction time."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentMetadata:
    name: str
    display_name: str
    description: str
    delegatable: bool = False


AGENT_METADATA: dict[str, AgentMetadata] = {
    "document_agent": AgentMetadata(
        name="document_agent",
        display_name="Document Agent",
        description=(
            "Use it when the user needs structured data extracted from a document, "
            "or when deep document analysis with precise field matching is required.\n\n"
            "Delegate to the Document Agent when:\n"
            "- The user provides a schema and asks for specific fields to be extracted from a document.\n"
            "- The task requires accurate, verbatim extraction from document content.\n"
            "- You need to locate and retrieve information across multiple document chunks.\n\n"
            "Do NOT delegate when:\n"
            "- The question is a simple lookup your document-grounded mode can answer directly.\n"
            "- No document or file_id is involved.\n\n"
            "The Document Agent returns a JSON array with extracted values and their locations "
            "in the document. Present the findings in a readable format unless the user asks for raw JSON."
        ),
        delegatable=True,
    ),
    "validation_agent": AgentMetadata(
        name="validation_agent",
        display_name="Validation Agent",
        description=(
            "Use it whenever a factual claim needs to be verified against "
            "real-world sources.\n\n"
            "Delegate to the Validation Agent when:\n"
            "- The user explicitly asks to verify, check, or validate a piece of information.\n"
            "- You extracted a value from a document and the user wants to confirm it is accurate.\n"
            "- You are uncertain about a factual claim and a web search would resolve it.\n\n"
            "Do NOT delegate when:\n"
            "- The answer is definitively contained in the document and no external check is needed.\n"
            "- The question is purely creative, conversational, or opinion-based.\n\n"
            "When validation URLs are explicitly provided, the agent fetches those pages directly\n"
            "using the web_page_content tool before falling back to a general web search.\n\n"
            "When the Validation Agent returns its JSON result, present the findings clearly to\n"
            "the user — do not expose the raw JSON unless the user asks for it."
        ),
        delegatable=True,
    ),
}


def get_delegatable_agents() -> list[AgentMetadata]:
    """Return agents with delegatable=True, in insertion order."""
    return [m for m in AGENT_METADATA.values() if m.delegatable]
