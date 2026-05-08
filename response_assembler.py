"""
response_assembler.py — Format an ordered list of chain results into labelled blocks.

Pure string logic — no LLM involvement.

Public interface:
    assemble(results: list[dict]) -> str
"""


def assemble(results: list[dict]) -> str:
    """Format an ordered list of {intent, label, response} dicts into a string.

    Each block is rendered as:
        **{label}:**
        {response}

    Multiple blocks are separated by a blank line. Input order is preserved.

    Args:
        results: Ordered list of dicts with keys 'label' and 'response'.
                 (The 'intent' key is accepted but not used in formatting.)

    Returns:
        A formatted string of sequential labelled blocks, or an empty string
        if results is empty.
    """
    if not results:
        return ""

    blocks = [f"**{item['label']}:**\n{item['response']}" for item in results]
    return "\n\n".join(blocks)
