from __future__ import annotations
from typing import Any

from ._base import BasePlaceholder, ml


class IntroPlaceholder(BasePlaceholder):
    keywords = ["intro", "introduction"]

    @classmethod
    def format(cls, introduction: str, **ctx) -> str:
        return ml("Intro", [introduction])

    @classmethod
    def parse(cls, content: str) -> dict[str, Any]:
        return {
            "type": "intro",
            "text": content.strip(),
        }
