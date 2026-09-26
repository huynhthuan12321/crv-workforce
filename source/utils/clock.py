from datetime import datetime
from zoneinfo import ZoneInfo

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


class Clock:
    def now(self) -> datetime:
        return datetime.now(VIETNAM_TZ)


class FakeClock(Clock):
    def __init__(self, value: datetime):
        self.value = value

    def now(self) -> datetime:
        return self.value
