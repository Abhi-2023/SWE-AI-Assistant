import contextlib
import json
import re


def parse_llm_json(response: str) -> dict:
    """
    Robustly parse JSON from LLM response.
    Handles markdown code fences, extra whitespace,
    and special characters in code content.
    """
    response = response.strip()

    # Strip markdown fences
    if response.startswith("```"):
        lines   = response.split("\n")
        lines   = [l for l in lines if not l.strip().startswith("```")]
        response = "\n".join(lines)
        response = response.removeprefix("json")
    response = response.strip()

    # Try direct parse
    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(response)
    if match := re.search(r'\{.*\}', response, re.DOTALL):
        with contextlib.suppress(json.JSONDecodeError):
            return json.loads(match.group())
    raise ValueError(f"Could not parse JSON from LLM response:\n{response[:300]}")