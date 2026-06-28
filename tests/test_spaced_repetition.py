"""Tests for eduvis.core.spaced_repetition."""

import datetime
from eduvis.core.spaced_repetition import (
    SpacedRepetitionRecord,
    SpacedRepetitionSchedule,
    update_review_schedule,
    get_due_elements,
    get_schedule_summary,
    _DEFAULT_EASE,
    _MIN_EASE,
)

TODAY = datetime.date.today().isoformat()
YESTERDAY = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
TOMORROW = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
FAR_FUTURE = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()


# ---------------------------------------------------------------------------
# SpacedRepetitionRecord
# ---------------------------------------------------------------------------

class TestSpacedRepetitionRecord:
    def test_defaults(self):
        rec = SpacedRepetitionRecord(element_id="q1")
        assert rec.interval_days == 0
        assert rec.ease_factor == _DEFAULT_EASE
        assert rec.repetitions == 0

    def test_to_dict_round_trip(self):
        rec = SpacedRepetitionRecord(
            element_id="q1", interval_days=6, ease_factor=2.3,
            repetitions=2, last_reviewed_at=TODAY, next_review_at=TOMORROW,
        )
        d = rec.to_dict()
        rec2 = SpacedRepetitionRecord.from_dict(d)
        assert rec2.element_id == "q1"
        assert rec2.interval_days == 6
        assert abs(rec2.ease_factor - 2.3) < 0.01
        assert rec2.repetitions == 2
        assert rec2.next_review_at == TOMORROW


# ---------------------------------------------------------------------------
# SpacedRepetitionSchedule
# ---------------------------------------------------------------------------

class TestSpacedRepetitionSchedule:
    def test_get_returns_none_for_unknown(self):
        s = SpacedRepetitionSchedule()
        assert s.get("unknown") is None

    def test_set_and_get(self):
        s = SpacedRepetitionSchedule()
        rec = SpacedRepetitionRecord(element_id="q1")
        s.set(rec)
        assert s.get("q1") is rec

    def test_to_dict_round_trip(self):
        s = SpacedRepetitionSchedule()
        s.set(SpacedRepetitionRecord(element_id="q1", interval_days=3))
        s.set(SpacedRepetitionRecord(element_id="q2", interval_days=7))
        d = s.to_dict()
        s2 = SpacedRepetitionSchedule.from_dict(d)
        assert "q1" in s2.records
        assert s2.records["q2"].interval_days == 7


# ---------------------------------------------------------------------------
# update_review_schedule
# ---------------------------------------------------------------------------

class TestUpdateReviewSchedule:
    def test_returns_new_schedule(self):
        s = SpacedRepetitionSchedule()
        s2 = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        assert s2 is not s

    def test_first_correct_sets_interval_1(self):
        s = SpacedRepetitionSchedule()
        s2 = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        assert s2.records["q1"].interval_days == 1

    def test_second_correct_sets_interval_6(self):
        s = SpacedRepetitionSchedule()
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        assert s.records["q1"].interval_days == 6

    def test_third_correct_multiplies_by_ease(self):
        s = SpacedRepetitionSchedule()
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        ease = s.records["q1"].ease_factor
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        expected = max(1, round(6 * ease))
        assert s.records["q1"].interval_days == expected

    def test_wrong_answer_resets_repetitions(self):
        s = SpacedRepetitionSchedule()
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        s = update_review_schedule(s, "q1", is_correct=False, reviewed_at=TODAY)
        rec = s.records["q1"]
        assert rec.repetitions == 0
        assert rec.interval_days == 1

    def test_wrong_answer_decreases_ease(self):
        s = SpacedRepetitionSchedule()
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        ease_before = s.records["q1"].ease_factor
        s = update_review_schedule(s, "q1", is_correct=False, reviewed_at=TODAY)
        assert s.records["q1"].ease_factor < ease_before

    def test_ease_never_falls_below_minimum(self):
        s = SpacedRepetitionSchedule()
        for _ in range(20):
            s = update_review_schedule(s, "q1", is_correct=False, reviewed_at=TODAY)
        assert s.records["q1"].ease_factor >= _MIN_EASE

    def test_next_review_at_set_correctly(self):
        s = SpacedRepetitionSchedule()
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        rec = s.records["q1"]
        expected = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        assert rec.next_review_at == expected

    def test_last_reviewed_at_set(self):
        s = SpacedRepetitionSchedule()
        s = update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        assert s.records["q1"].last_reviewed_at == TODAY

    def test_original_schedule_unchanged(self):
        s = SpacedRepetitionSchedule()
        update_review_schedule(s, "q1", is_correct=True, reviewed_at=TODAY)
        assert "q1" not in s.records

    def test_custom_quality_score(self):
        s = SpacedRepetitionSchedule()
        s = update_review_schedule(s, "q1", is_correct=True, quality=3, reviewed_at=TODAY)
        # quality=3 passes but ease should be lower than quality=5
        ease_q3 = s.records["q1"].ease_factor
        s2 = SpacedRepetitionSchedule()
        s2 = update_review_schedule(s2, "q1", is_correct=True, quality=5, reviewed_at=TODAY)
        ease_q5 = s2.records["q1"].ease_factor
        assert ease_q3 < ease_q5


# ---------------------------------------------------------------------------
# get_due_elements
# ---------------------------------------------------------------------------

class TestGetDueElements:
    def _schedule_with_dates(self) -> SpacedRepetitionSchedule:
        s = SpacedRepetitionSchedule()
        for eid, nxt in [("past", YESTERDAY), ("today", TODAY), ("future", FAR_FUTURE)]:
            rec = SpacedRepetitionRecord(element_id=eid, next_review_at=nxt, repetitions=1)
            s.set(rec)
        return s

    def test_returns_past_and_today(self):
        s = self._schedule_with_dates()
        due = get_due_elements(s, as_of_date=TODAY)
        assert "past" in due
        assert "today" in due
        assert "future" not in due

    def test_untracked_element_is_always_due(self):
        s = SpacedRepetitionSchedule()
        due = get_due_elements(s, element_ids=["untracked"])
        assert "untracked" in due

    def test_filters_to_element_ids_list(self):
        s = self._schedule_with_dates()
        due = get_due_elements(s, element_ids=["past", "future"], as_of_date=TODAY)
        assert "past" in due
        assert "future" not in due
        assert "today" not in due

    def test_all_tracked_returned_when_no_filter(self):
        s = self._schedule_with_dates()
        # Only past and today should be due
        due = get_due_elements(s, as_of_date=TODAY)
        assert set(due) == {"past", "today"}

    def test_future_date_returns_all(self):
        s = self._schedule_with_dates()
        due = get_due_elements(s, as_of_date=FAR_FUTURE)
        assert "past" in due
        assert "today" in due
        assert "future" in due


# ---------------------------------------------------------------------------
# get_schedule_summary
# ---------------------------------------------------------------------------

class TestGetScheduleSummary:
    def test_returns_expected_keys(self):
        s = SpacedRepetitionSchedule()
        summary = get_schedule_summary(s)
        for k in ("total_tracked", "due_today", "overdue", "upcoming",
                  "average_ease_factor", "due_element_ids", "overdue_element_ids"):
            assert k in summary

    def test_empty_schedule_zeros(self):
        s = SpacedRepetitionSchedule()
        summary = get_schedule_summary(s)
        assert summary["total_tracked"] == 0
        assert summary["due_today"] == 0
        assert summary["overdue"] == 0

    def test_counts_due_and_overdue_correctly(self):
        s = SpacedRepetitionSchedule()
        s.set(SpacedRepetitionRecord(element_id="past", next_review_at=YESTERDAY, repetitions=1))
        s.set(SpacedRepetitionRecord(element_id="today", next_review_at=TODAY, repetitions=1))
        s.set(SpacedRepetitionRecord(element_id="future", next_review_at=FAR_FUTURE, repetitions=1))
        summary = get_schedule_summary(s)
        assert summary["total_tracked"] == 3
        assert summary["due_today"] == 1
        assert summary["overdue"] == 1
        assert summary["upcoming"] == 1

    def test_average_ease_calculated(self):
        s = SpacedRepetitionSchedule()
        s.set(SpacedRepetitionRecord(element_id="q1", ease_factor=2.5))
        s.set(SpacedRepetitionRecord(element_id="q2", ease_factor=2.0))
        summary = get_schedule_summary(s)
        assert abs(summary["average_ease_factor"] - 2.25) < 0.01
