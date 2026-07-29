"""KxLang (DEFCOM) parser — Kx-Defender proprietary command language."""

from __future__ import annotations

import json
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LEXICON_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "catalog" / "kxlang_lexicon.json"

SCOPE_MAP = {
    "lab": "lab",
    "owned": "owned",
    "pact": "engagement",
    "engagement": "engagement",
}


class KxLangError(ValueError):
    """Invalid KxLang grammar or unknown verb/object."""


@dataclass
class KxCommand:
    verb: str
    obj: str
    module: str
    params: dict[str, Any] = field(default_factory=dict)
    raw: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": "KxLang",
            "codename": "DEFCOM",
            "verb": self.verb,
            "object": self.obj,
            "module": self.module,
            "params": self.params,
            "raw": self.raw,
        }


def load_lexicon(path: Path | None = None) -> dict[str, Any]:
    lexicon_path = path or LEXICON_PATH
    if not lexicon_path.is_file():
        raise KxLangError(f"lexicon missing: {lexicon_path}")
    return json.loads(lexicon_path.read_text(encoding="utf-8"))


def list_verbs(lexicon: dict[str, Any] | None = None) -> dict[str, Any]:
    lex = lexicon or load_lexicon()
    out = {}
    for verb, meta in lex.get("verbs", {}).items():
        out[verb] = {
            "role": meta.get("role"),
            "family": meta.get("family"),
            "default_object": meta.get("default_object"),
            "objects": sorted(meta.get("objects", {}).keys()),
        }
    return out


def resolve_module(verb: str, obj: str, lexicon: dict[str, Any] | None = None) -> tuple[str, str, dict[str, Any]]:
    """Return (object_key, module_name, defaults)."""
    lex = lexicon or load_lexicon()
    verbs = lex.get("verbs", {})
    key = verb.lower()
    if key not in verbs:
        raise KxLangError(f"unknown verb {verb!r}. try: kx lexicon")
    meta = verbs[key]
    objects = meta.get("objects", {})
    object_key = (obj or "").lower()
    default = meta.get("default_object")
    if object_key in {"", "_", "-"}:
        if not default:
            raise KxLangError(f"verb {key!r} requires an object")
        object_key = default
    if object_key not in objects:
        raise KxLangError(
            f"unknown object {obj!r} for verb {key!r}. "
            f"objects: {', '.join(sorted(objects))}"
        )
    module = objects[object_key]
    defaults = dict(meta.get("defaults", {}))
    if key == "nexus":
        if object_key in {"listen", "havoc", "sliver"}:
            defaults["action"] = "start_listener"
        else:
            defaults["action"] = "status"
    return object_key, module, defaults


def parse_argv(argv: list[str], lexicon: dict[str, Any] | None = None) -> KxCommand:
    """Parse `kx <verb> <object> [flags]` argv (without program name)."""
    if not argv:
        raise KxLangError("empty command. usage: kx <VERB> <OBJECT> --scope lab [--sim|--live]")

    head = argv[0].lower()
    if head in {"lexicon", "help", "verbs"}:
        return KxCommand(verb=head, obj=argv[1] if len(argv) > 1 else "", module="", params={}, raw=" ".join(argv))

    verb = argv[0].lower()
    rest = argv[1:]
    obj = ""
    if rest and not rest[0].startswith("-"):
        obj = rest[0]
        rest = rest[1:]

    lex = lexicon or load_lexicon()
    obj, module, defaults = resolve_module(verb, obj, lex)

    params: dict[str, Any] = dict(defaults)
    params["mode"] = "simulate"
    scope = None
    i = 0
    while i < len(rest):
        tok = rest[i]
        if tok in {"--sim"}:
            params["mode"] = "simulate"
        elif tok in {"--live"}:
            params["mode"] = "execute"
        elif tok == "--scope":
            i += 1
            if i >= len(rest):
                raise KxLangError("--scope requires a value")
            scope_raw = rest[i].lower()
            if scope_raw not in SCOPE_MAP:
                raise KxLangError("--scope must be lab|owned|pact")
            scope = SCOPE_MAP[scope_raw]
        elif tok == "--at":
            i += 1
            if i >= len(rest):
                raise KxLangError("--at requires a value")
            params["target"] = rest[i]
            # contextual mirrors
            if verb == "crack":
                params["essid"] = rest[i]
            if verb in {"roast", "breach"}:
                params.setdefault("domain", rest[i])
        elif tok == "--realm":
            i += 1
            if i >= len(rest):
                raise KxLangError("--realm requires a value")
            params["domain"] = rest[i]
            params.setdefault("target", rest[i])
        elif tok == "--url":
            i += 1
            if i >= len(rest):
                raise KxLangError("--url requires a value")
            params["url"] = rest[i]
            params.setdefault("target", rest[i])
        elif tok == "--bind":
            i += 1
            if i >= len(rest):
                raise KxLangError("--bind requires host:port")
            bind = rest[i]
            if ":" not in bind:
                raise KxLangError("--bind must be host:port")
            host, port_s = bind.rsplit(":", 1)
            params["host"] = host
            params["port"] = int(port_s)
            params.setdefault("target", host)
        elif tok == "--pact-file":
            i += 1
            if i >= len(rest):
                raise KxLangError("--pact-file requires a path")
            params["engagement_file"] = rest[i]
        elif tok == "--with":
            i += 1
            if i >= len(rest) or "=" not in rest[i]:
                raise KxLangError("--with requires key=value")
            k, v = rest[i].split("=", 1)
            params[k] = v
        else:
            raise KxLangError(f"unknown flag {tok!r}")
        i += 1

    if scope is None:
        raise KxLangError("--scope is required (lab|owned|pact)")
    params["authorized_scope"] = scope

    # nexus listen convenience
    if verb == "nexus" and obj in {"listen", "havoc", "sliver"}:
        params.setdefault("action", "start_listener")
        params.setdefault("host", "127.0.0.1")
        params.setdefault("port", 4455 if obj != "sliver" else 4456)

    return KxCommand(verb=verb, obj=obj, module=module, params=params, raw=" ".join(argv))


def parse_line(line: str, lexicon: dict[str, Any] | None = None) -> KxCommand:
    return parse_argv(shlex.split(line), lexicon=lexicon)
