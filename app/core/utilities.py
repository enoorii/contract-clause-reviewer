import re


def extract_json_from_string(content: str) -> str:
    """
    Extract JSON from the string content.
    Handles markdown code blocks and plain JSON.
    """
    # Try to find JSON in markdown code blocks
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if json_match:
        return json_match.group(1)

    # Try to find JSON object directly (greedy but safe)
    json_match = re.search(r"\{.*\}", content, re.DOTALL)
    if json_match:
        return json_match.group(0)

    # If no JSON found, return original content (will fail parsing)
    return content
