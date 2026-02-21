"""Prompt builder for document field extraction."""


def build_extraction_prompt(schema_fields: list[dict], file_id: str) -> str:
    """Build a prompt instructing the agent to extract schema fields from a document.

    Args:
        schema_fields: List of dicts with 'key' and 'description' keys.
        file_id: The stored file UUID the agent should read/search.

    Returns:
        A prompt string for the document agent.
    """
    field_lines = "\n".join(
        f"- {f['key']}: {f.get('description', '')}" for f in schema_fields
    )

    return f"""\
Extract the following fields from the document identified by file_id.

Document file_id: {file_id}

Fields to extract (keys are case-sensitive and must match exactly):
{field_lines}

Follow all extraction and output rules defined in the system prompt.
Return ONLY a valid JSON array.
Include ALL schema keys in the output.
Do not infer or guess missing values.
"""
