"""Per-verb.object parameter schema + CLI helpers.

Ports the retired web UI's PARAM_SCHEMA to the terminal:
  - `schema_for(verb, obj)`  → list of field dicts
  - `parse_command_form(argv)` → dict of flags already set + remaining tokens
  - `augment_argv(argv, values)` → argv with additional flag/value pairs appended
  - `prompt_interactive(schema, prefilled, stream_in, stream_out)` → dict

The web UI used the same shape; keeping the data in a JSON file lets any
front-end (this CLI, the Node client, a future Textual TUI) share it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, TextIO

SCHEMA_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "catalog" / "param_schema.json"

# Flags that consume the following token as their value.
VALUE_TAKING_FLAGS = {
    "--scope", "--at", "--realm", "--url", "--bind",
    "--pid", "--path", "--pact-file", "--with", "--sample",
}


def _load() -> dict[str, Any]:
    if not SCHEMA_PATH.is_file():
        return {"schemas": {}, "verb_fallback": {}}
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def schema_for(
    verb: str,
    obj: str = "",
    lexicon_verbs: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Return (fields, schema_key). Falls back to verb-level generic schema.

    When ``obj`` is empty and the lexicon knows a default object for ``verb``,
    we try that object's schema first.
    """
    data = _load()
    schemas = data.get("schemas", {})
    fallback = data.get("verb_fallback", {})

    verb_l = (verb or "").lower()
    obj_l = (obj or "").lower()

    if not verb_l:
        return [], None

    key = f"{verb_l}.{obj_l}"
    if key in schemas:
        return list(schemas[key]), key

    # Try default_object from lexicon
    if lexicon_verbs and verb_l in lexicon_verbs:
        default = (lexicon_verbs[verb_l] or {}).get("default_object")
        if default:
            dkey = f"{verb_l}.{default}"
            if dkey in schemas:
                return list(schemas[dkey]), dkey

    if verb_l in fallback:
        return list(fallback[verb_l]), f"{verb_l}.*"

    return [], None


def parse_command_form(argv: Iterable[str]) -> dict[str, Any]:
    """Extract verb, obj, and already-present flags from argv (or a raw string).

    Returns::
        {"verb": str, "obj": str, "flags_set": set[str], "flag_values": {flag: value}}
    """
    tokens: list[str]
    if isinstance(argv, str):
        # very light split; the CLI never quotes flags themselves
        tokens = [t for t in argv.strip().split() if t]
    else:
        tokens = [t for t in argv if t]

    verb = tokens[0] if tokens else ""
    obj = ""
    i = 1
    if len(tokens) > 1 and not tokens[1].startswith("-"):
        obj = tokens[1]
        i = 2

    flags_set: set[str] = set()
    flag_values: dict[str, str] = {}
    while i < len(tokens):
        tok = tokens[i]
        if tok.startswith("--"):
            flags_set.add(tok)
            if tok in VALUE_TAKING_FLAGS and i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                flag_values[tok] = tokens[i + 1]
                i += 2
                continue
        i += 1

    return {"verb": verb, "obj": obj, "flags_set": flags_set, "flag_values": flag_values}


def augment_argv(argv: list[str], values: list[tuple[str, str]]) -> list[str]:
    """Append (flag, value) pairs to argv unless the flag is already present."""
    parsed = parse_command_form(argv)
    already = parsed["flags_set"]
    out = list(argv)
    for flag, value in values:
        if not value or flag in already:
            continue
        out.extend([flag, value])
    return out


def collect_from_prompts(
    schema: list[dict[str, Any]],
    already_set: set[str],
    stream_in: TextIO,
    stream_out: TextIO,
) -> list[tuple[str, str]]:
    """Ask the user for each schema field not already in the command."""
    collected: list[tuple[str, str]] = []
    for field in schema:
        flag = field.get("flag")
        if not flag or flag in already_set:
            continue
        label = field.get("label") or flag
        hint = field.get("hint") or ""
        default = field.get("default") or ""
        required = field.get("required", False)
        req_mark = "*" if required else " "
        placeholder = field.get("placeholder") or ""
        default_hint = f" [{default}]" if default else (f" [{placeholder}]" if placeholder else "")
        prompt = f"  {req_mark} {label} ({flag}){default_hint}"
        if hint:
            prompt += f"  — {hint}"
        stream_out.write(prompt + "\n    > ")
        stream_out.flush()
        try:
            raw = stream_in.readline()
        except (KeyboardInterrupt, EOFError):
            stream_out.write("\n")
            break
        value = (raw or "").strip()
        if not value and default:
            value = default
        if not value and required:
            stream_out.write("    (required — using placeholder default in simulate)\n")
            value = placeholder or "auto"
        if value:
            collected.append((flag, value))
    return collected
