"""The publish workflow as a table (docs/SPEC.md §6).

``TRANSITIONS[from]`` is the set of statuses a staff transition may target.
``scheduled -> draft`` is "cancel the schedule": the row falls back to
``published`` when a live revision exists, else to ``draft``.
"""
from __future__ import annotations

from .models import Status

DRAFT, SCHEDULED, PUBLISHED, ARCHIVED = Status.DRAFT, Status.SCHEDULED, Status.PUBLISHED, Status.ARCHIVED

TRANSITIONS: dict[str, frozenset[str]] = {
    DRAFT: frozenset({SCHEDULED, PUBLISHED, ARCHIVED}),
    SCHEDULED: frozenset({DRAFT, SCHEDULED, PUBLISHED, ARCHIVED}),
    PUBLISHED: frozenset({SCHEDULED, PUBLISHED, ARCHIVED}),
    ARCHIVED: frozenset({DRAFT}),
}

#: Statuses a transition request may name.
TARGETS = (DRAFT, SCHEDULED, PUBLISHED, ARCHIVED)


def allowed(from_status: str, to_status: str) -> bool:
    return to_status in TRANSITIONS.get(from_status, frozenset())


__all__ = ["ARCHIVED", "DRAFT", "PUBLISHED", "SCHEDULED", "TARGETS", "TRANSITIONS", "allowed"]
