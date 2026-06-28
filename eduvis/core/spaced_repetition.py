"""EduVis — Spaced Repetition Scheduler (SM-2 algorithm).

Implements the SuperMemo 2 (SM-2) spaced repetition algorithm adapted for
EduVis lesson elements.  Three public types and three public functions:

  SpacedRepetitionRecord
      Per-element review state: next_review_at, interval_days, ease_factor,
      repetitions (total review count), and last_reviewed_at.

  SpacedRepetitionSchedule
      Container for all SpacedRepetitionRecords keyed by element_id.
      Supports serialisation to/from plain dicts.

  update_review_schedule(schedule, element_id, is_correct, quality)
      Apply SM-2 update for one review event.  quality is 0–5 (SM-2 scale);
      when omitted it defaults to 5 (perfect) for correct and 1 for wrong.
      Returns the updated schedule (immutable-style: new schedule instance).

  get_due_elements(schedule, element_ids, as_of_date)
      Return the subset of element_ids whose next_review_at is on or before
      as_of_date (defaults to today).

  get_schedule_summary(schedule)
      Aggregate stats across all records: total tracked, due today, overdue,
      upcoming, average ease_factor.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

# SM-2 constants
_MIN_EASE = 1.3
_DEFAULT_EASE = 2.5
_FIRST_INTERVAL = 1       # days after first correct
_SECOND_INTERVAL = 6      # days after second consecutive correct


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class SpacedRepetitionRecord:
    """Review state for a single lesson element."""
    element_id: str
    interval_days: int = 0
    ease_factor: float = _DEFAULT_EASE
    repetitions: int = 0
    last_reviewed_at: str | None = None    # ISO date string
    next_review_at: str | None = None      # ISO date string

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "interval_days": self.interval_days,
            "ease_factor": round(self.ease_factor, 4),
            "repetitions": self.repetitions,
            "last_reviewed_at": self.last_reviewed_at,
            "next_review_at": self.next_review_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpacedRepetitionRecord:
        return cls(
            element_id=str(data.get("element_id", "")),
            interval_days=int(data.get("interval_days", 0)),
            ease_factor=float(data.get("ease_factor", _DEFAULT_EASE)),
            repetitions=int(data.get("repetitions", 0)),
            last_reviewed_at=data.get("last_reviewed_at"),
            next_review_at=data.get("next_review_at"),
        )


class SpacedRepetitionSchedule:
    """Collection of SpacedRepetitionRecords keyed by element_id."""

    def __init__(self) -> None:
        self.records: dict[str, SpacedRepetitionRecord] = {}

    def get(self, element_id: str) -> SpacedRepetitionRecord | None:
        return self.records.get(element_id)

    def set(self, record: SpacedRepetitionRecord) -> None:
        self.records[record.element_id] = record

    def to_dict(self) -> dict[str, Any]:
        return {eid: rec.to_dict() for eid, rec in self.records.items()}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SpacedRepetitionSchedule:
        schedule = cls()
        for eid, rec_data in data.items():
            if isinstance(rec_data, dict):
                rec_data["element_id"] = eid
                schedule.records[eid] = SpacedRepetitionRecord.from_dict(rec_data)
        return schedule


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def update_review_schedule(
    schedule: SpacedRepetitionSchedule,
    element_id: str,
    is_correct: bool,
    quality: int | None = None,
    reviewed_at: str | None = None,
) -> SpacedRepetitionSchedule:
    """Apply an SM-2 update for one review event and return the new schedule.

    quality — SM-2 quality score 0-5.  When None:
        5 (perfect recall) for correct answers
        1 (incorrect but remembered after seeing) for wrong answers
    reviewed_at — ISO date string; defaults to today.
    """
    if quality is None:
        quality = 5 if is_correct else 1
    quality = max(0, min(5, quality))

    today_str = reviewed_at or datetime.date.today().isoformat()
    today = _parse_date(today_str)

    existing = schedule.get(element_id)
    rec = SpacedRepetitionRecord(
        element_id=element_id,
        interval_days=existing.interval_days if existing else 0,
        ease_factor=existing.ease_factor if existing else _DEFAULT_EASE,
        repetitions=existing.repetitions if existing else 0,
        last_reviewed_at=existing.last_reviewed_at if existing else None,
        next_review_at=existing.next_review_at if existing else None,
    )

    if quality < 3:
        # Failed: reset repetitions and interval; re-show soon
        rec.repetitions = 0
        rec.interval_days = 1
    else:
        # Passed: apply SM-2 interval progression
        if rec.repetitions == 0:
            rec.interval_days = _FIRST_INTERVAL
        elif rec.repetitions == 1:
            rec.interval_days = _SECOND_INTERVAL
        else:
            rec.interval_days = max(1, round(rec.interval_days * rec.ease_factor))
        rec.repetitions += 1

    # Update ease factor: EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    rec.ease_factor = max(
        _MIN_EASE,
        rec.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
    )

    rec.last_reviewed_at = today_str
    next_date = today + datetime.timedelta(days=rec.interval_days)
    rec.next_review_at = next_date.isoformat()

    # Return a new schedule with the updated record
    new_schedule = SpacedRepetitionSchedule()
    new_schedule.records = dict(schedule.records)
    new_schedule.set(rec)
    return new_schedule


def get_due_elements(
    schedule: SpacedRepetitionSchedule,
    element_ids: list[str] | None = None,
    as_of_date: str | None = None,
) -> list[str]:
    """Return element IDs whose next_review_at is on or before as_of_date.

    element_ids — optional filter list; if None, checks all tracked elements.
    as_of_date  — ISO date string; defaults to today.
    """
    cutoff = _parse_date(as_of_date or datetime.date.today().isoformat())
    candidates = element_ids if element_ids is not None else list(schedule.records.keys())

    due: list[str] = []
    for eid in candidates:
        rec = schedule.records.get(eid)
        if rec is None:
            # Never reviewed → always due
            due.append(eid)
            continue
        if rec.next_review_at is None:
            due.append(eid)
            continue
        review_date = _parse_date(rec.next_review_at)
        if review_date <= cutoff:
            due.append(eid)

    return due


def get_schedule_summary(schedule: SpacedRepetitionSchedule) -> dict[str, Any]:
    """Aggregate statistics across all records in the schedule."""
    today = datetime.date.today()
    total = len(schedule.records)

    due_today: list[str] = []
    overdue: list[str] = []
    upcoming: list[str] = []
    ease_values: list[float] = []

    for eid, rec in schedule.records.items():
        ease_values.append(rec.ease_factor)
        if rec.next_review_at is None:
            due_today.append(eid)
            continue
        review_date = _parse_date(rec.next_review_at)
        if review_date < today:
            overdue.append(eid)
        elif review_date == today:
            due_today.append(eid)
        else:
            upcoming.append(eid)

    avg_ease = round(sum(ease_values) / len(ease_values), 4) if ease_values else 0.0

    return {
        "total_tracked": total,
        "due_today": len(due_today),
        "overdue": len(overdue),
        "upcoming": len(upcoming),
        "average_ease_factor": avg_ease,
        "due_element_ids": sorted(due_today),
        "overdue_element_ids": sorted(overdue),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(date_str: str) -> datetime.date:
    """Parse ISO date string (YYYY-MM-DD or ISO datetime)."""
    try:
        return datetime.date.fromisoformat(date_str[:10])
    except ValueError:
        return datetime.date.today()
