"""Manifest and dependency pin guards (spec 0015)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pydmvl

_ROOT = Path(__file__).parent.parent
_MANIFEST_PATH = _ROOT / "custom_components" / "dmvl" / "manifest.json"
_REQUIREMENTS_PATH = _ROOT / "requirements_dev.txt"


def _manifest() -> dict[str, object]:
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _requirements_pin(name: str) -> str:
    text = _REQUIREMENTS_PATH.read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(name)}==(\S+)$", text, flags=re.MULTILINE)
    assert match is not None, f"{name} pin not found in requirements_dev.txt"
    return match.group(1)


def _manifest_pin(name: str) -> str:
    requirements = _manifest()["requirements"]
    assert isinstance(requirements, list)
    pins = [
        requirement.split("==", 1)[1]
        for requirement in requirements
        if isinstance(requirement, str) and requirement.startswith(f"{name}==")
    ]
    assert pins, f"{name} pin not found in manifest.json"
    return pins[0]


def test_pydmvl_pin_matches_installed_version() -> None:
    assert _manifest_pin("pydmvl") == _requirements_pin("pydmvl") == pydmvl.__version__
