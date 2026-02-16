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
Extract the following fields from the document.
Use the file_id to read or search the document using your available tools.

Document file_id: {file_id}

Fields to extract:
{field_lines}

Instructions:
- Return ONLY a valid JSON array, no other text
- Each item: {{"key": "field_name", "extraction": "value or null", "location": {{"page_num": N or null, "chunk_num": N or null}}}}
- ALL schema keys must appear in the output
- Set extraction and location to null if the value is not found in the document
- If a field has multiple values (e.g. multiple phone numbers), return separate entries \
with numbered keys: phone_number_1, phone_number_2, etc.
- For location, page_num is the 1-based PDF page number, chunk_num is the chunk index \
from search results (if available)"""
