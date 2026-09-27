from datetime import date

from source.services.workforce import ReportService


def test_report_bounds_week_starts_monday():
    assert ReportService.bounds("week", date(2026, 9, 27)) == (date(2026, 9, 21), date(2026, 9, 27))


def test_report_bounds_month_uses_calendar_month():
    assert ReportService.bounds("month", date(2026, 2, 12)) == (date(2026, 2, 1), date(2026, 2, 28))
