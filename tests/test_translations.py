"""Localized integration title and translation-file structure (spec 0018)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import translation

_TRANSLATIONS_DIR = (
    Path(__file__).parent.parent / "custom_components" / "dmvl" / "translations"
)
_RU_TITLE = "Домовладелец+"
_EN_TITLE = "Domovladelets"


def _load(language: str) -> dict[str, Any]:
    return json.loads(
        (_TRANSLATIONS_DIR / f"{language}.json").read_text(encoding="utf-8")
    )


@pytest.mark.parametrize(
    ("language", "expected"),
    [("ru", _RU_TITLE), ("en", _EN_TITLE)],
)
async def test_localized_integration_title(
    hass: HomeAssistant, language: str, expected: str
) -> None:
    """The frontend-facing title follows the language of the translation file."""
    strings = await translation.async_get_translations(
        hass, language, "title", {"dmvl"}
    )
    assert strings["component.dmvl.title"] == expected


@pytest.mark.parametrize("language", ["en", "ru"])
def test_translation_files_declare_string_title(language: str) -> None:
    data = _load(language)
    assert isinstance(data.get("title"), str)
    assert data["title"]


def test_english_title_has_no_cyrillic() -> None:
    title = _load("en")["title"]
    assert not any("\u0400" <= char <= "\u04ff" for char in title)
