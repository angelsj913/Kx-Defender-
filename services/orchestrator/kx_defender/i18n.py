"""UI language preference (en | ko) for Kx CLI / shell."""

from __future__ import annotations

import json
import os
from pathlib import Path

SUPPORTED = ("en", "ko")
ALIASES = {
    "en": "en",
    "english": "en",
    "eng": "en",
    "us": "en",
    "ko": "ko",
    "kr": "ko",
    "korean": "ko",
    "kor": "ko",
    "한국어": "ko",
    "한글": "ko",
}


def config_path() -> Path:
    override = os.environ.get("KX_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".kx-defender" / "config.json"


def _read_config() -> dict:
    path = config_path()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _write_config(data: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_lang(value: str | None) -> str | None:
    if value is None:
        return None
    key = value.strip().lower()
    return ALIASES.get(key)


def get_lang() -> str:
    env = os.environ.get("KX_LANG") or os.environ.get("KX_LANGUAGE")
    if env:
        norm = normalize_lang(env)
        if norm:
            return norm
    cfg = _read_config()
    norm = normalize_lang(str(cfg.get("lang", "")))
    return norm or "en"


def set_lang(value: str) -> str:
    norm = normalize_lang(value)
    if not norm:
        raise ValueError(f"unsupported language {value!r}; use: en | ko")
    cfg = _read_config()
    cfg["lang"] = norm
    _write_config(cfg)
    os.environ["KX_LANG"] = norm
    return norm


def t(en: str, ko: str, lang: str | None = None) -> str:
    return ko if (lang or get_lang()) == "ko" else en
