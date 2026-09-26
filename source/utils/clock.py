from datetime import datetime
from zoneinfo import ZoneInfo

from source.domain.workforce_errors import fail

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def to_vn(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise fail("INVALID_DATETIME", 422)
    return value.astimezone(VIETNAM_TZ)


class Clock:
    def now(self) -> datetime:
        return datetime.now(VIETNAM_TZ)


class FakeClock(Clock):
    def __init__(self, value: datetime):
        self.value = value

    def now(self) -> datetime:
        return self.value
