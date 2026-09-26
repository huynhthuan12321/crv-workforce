from datetime import date, datetime
from decimal import Decimal

from source.utils.clock import VIETNAM_TZ


def _vn(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=VIETNAM_TZ)
    return value.astimezone(VIETNAM_TZ)


def iso_vn(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _vn(value).isoformat()


def fmt_time_vn(value: datetime | None) -> str:
    if value is None:
        return ""
    return _vn(value).strftime("%H:%M")


def fmt_date_vn(value: date | datetime | None) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        value = _vn(value).date()
    return value.strftime("%d/%m")


def fmt_money_vn(value: int | Decimal | float | None) -> str:
    amount = int(value or 0)
    return f"{amount:,}".replace(",", ".") + "đ"
