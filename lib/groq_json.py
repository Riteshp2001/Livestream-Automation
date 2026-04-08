from __future__ import annotations

import json
from json import JSONDecodeError


_VALID_SIMPLE_ESCAPES = {'"', "\\", "/", "b", "f", "n", "r", "t"}
_HEX_DIGITS = set("0123456789abcdefABCDEF")


def strip_groq_json_fences(content: str) -> str:
    cleaned = (content or "").strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def extract_json_object(content: str) -> str:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end < start:
        return content
    return content[start : end + 1]


def repair_groq_json(content: str) -> str:
    repaired: list[str] = []
    in_string = False
    i = 0
    content_length = len(content)

    while i < content_length:
        char = content[i]

        if not in_string:
            repaired.append(char)
            if char == '"':
                in_string = True
            i += 1
            continue

        if char == "\\":
            if i + 1 >= content_length:
                repaired.append("\\\\")
                i += 1
                continue

            next_char = content[i + 1]
            if next_char == "'":
                repaired.append("'")
                i += 2
                continue

            if next_char in _VALID_SIMPLE_ESCAPES:
                repaired.append("\\")
                repaired.append(next_char)
                i += 2
                continue

            if (
                next_char == "u"
                and i + 5 < content_length
                and all(digit in _HEX_DIGITS for digit in content[i + 2 : i + 6])
            ):
                repaired.append(content[i : i + 6])
                i += 6
                continue

            repaired.append("\\\\")
            i += 1
            continue

        if char == '"':
            in_string = False
            repaired.append(char)
            i += 1
            continue

        if char == "\r":
            repaired.append("\\r")
            i += 1
            continue

        if char == "\n":
            repaired.append("\\n")
            i += 1
            continue

        repaired.append(char)
        i += 1

    return "".join(repaired)


def parse_groq_json(content: str) -> dict:
    cleaned = strip_groq_json_fences(content)
    candidates: list[str] = []
    for candidate in (cleaned, extract_json_object(cleaned)):
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    last_error: JSONDecodeError | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate, strict=False)
        except JSONDecodeError as exc:
            last_error = exc

    for candidate in candidates:
        repaired = repair_groq_json(candidate)
        if repaired == candidate:
            continue
        try:
            return json.loads(repaired, strict=False)
        except JSONDecodeError as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise JSONDecodeError("No JSON object found in Groq response.", cleaned, 0)
