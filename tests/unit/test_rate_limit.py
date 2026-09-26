import pytest

from source.domain.workforce_errors import WorkforceError
from source.services.rate_limit import AttendanceRateLimiter


@pytest.mark.asyncio
async def test_attendance_rate_limiter_memory_uses_fake_clock_without_sleep():
    now = 1000.0
    limiter = AttendanceRateLimiter(now=lambda: now)

    await limiter.check(1, "check-in")

    with pytest.raises(WorkforceError) as exc_info:
        await limiter.check(1, "check-in")
    assert exc_info.value.code == "TOO_FAST"

    now += 3.1
    await limiter.check(1, "check-in")
