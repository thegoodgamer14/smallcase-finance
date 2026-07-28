"""Data-access errors (mapped to HTTP in the API layer)."""

from __future__ import annotations


class CuratedDataUnavailable(Exception):
    """Curated root or required table missing / unreadable."""

    def __init__(self, message: str = "Curated data is unavailable") -> None:
        super().__init__(message)
        self.message = message


class SmallcaseNotFound(Exception):
    """Unknown smallcase_id."""

    def __init__(self, smallcase_id: str) -> None:
        self.smallcase_id = smallcase_id
        super().__init__(f"Smallcase not found: {smallcase_id}")
