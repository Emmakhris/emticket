from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, date, time, timedelta
from typing import Iterable, List, Tuple, Optional

from django.utils import timezone

from .models import WorkingCalendar


@dataclass(frozen=True)
class TimeRange:
    start: time
    end: time


_WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


def _parse_hhmm(s: str) -> time:
    hh, mm = s.split(":")
    return time(int(hh), int(mm))


def _get_day_ranges(calendar: WorkingCalendar, d: date) -> List[TimeRange]:
    wd = _WEEKDAY_KEYS[d.weekday()]
    raw = (calendar.weekly_hours or {}).get(wd, [])
    out: List[TimeRange] = []
    for start_str, end_str in raw:
        out.append(TimeRange(_parse_hhmm(start_str), _parse_hhmm(end_str)))
    return out


def _is_holiday(calendar: WorkingCalendar, d: date) -> bool:
    holidays = set(calendar.holidays or [])
    return d.isoformat() in holidays


def _localize(calendar: WorkingCalendar, dt: datetime) -> datetime:
    tz = timezone.get_fixed_timezone(0)
    try:
        tz = timezone.pytz.timezone(calendar.timezone)  # type: ignore[attr-defined]
    except Exception:
        # If pytz isn't available (Django 5 uses zoneinfo), fall back to Django tz
        pass
    return dt.astimezone(tz)


def _to_utc(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc)


def add_working_minutes(calendar: WorkingCalendar, start_utc: datetime, minutes: int) -> datetime:
    """
    Adds working minutes according to calendar (weekly hours + holidays).
    Input and output are UTC-aware datetimes.

    This is robust and deterministic; performance is fine for SLA time windows
    (minutes/hours/days). If you expect very large durations, we can optimize.
    """
    if minutes <= 0:
        return start_utc

    start_local = _localize(calendar, start_utc)
    remaining = minutes
    cursor = start_local

    while remaining > 0:
        day = cursor.date()

        # skip holidays
        if _is_holiday(calendar, day):
            cursor = datetime.combine(day + timedelta(days=1), time(0, 0), cursor.tzinfo)
            continue

        ranges = _get_day_ranges(calendar, day)
        if not ranges:
            cursor = datetime.combine(day + timedelta(days=1), time(0, 0), cursor.tzinfo)
            continue

        progressed = False
        for r in ranges:
            window_start = datetime.combine(day, r.start, cursor.tzinfo)
            window_end = datetime.combine(day, r.end, cursor.tzinfo)

            # move into the window
            if cursor < window_start:
                cursor = window_start

            # if cursor is after this window, skip it
            if cursor >= window_end:
                continue

            available = int((window_end - cursor).total_seconds() // 60)
            if available <= 0:
                continue

            use = min(available, remaining)
            cursor = cursor + timedelta(minutes=use)
            remaining -= use
            progressed = True

            if remaining <= 0:
                break

        if not progressed:
            # move to next day
            cursor = datetime.combine(day + timedelta(days=1), time(0, 0), cursor.tzinfo)

    return _to_utc(cursor)
