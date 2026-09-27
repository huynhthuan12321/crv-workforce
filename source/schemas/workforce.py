from datetime import date
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class DataResponse(BaseModel, Generic[T]):
    data: T


class WorkSessionOut(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "id": 1,
        "employee_id": 10,
        "work_date": "2026-04-24",
        "check_in_at": "2026-04-24T08:12:00+07:00",
        "check_out_at": None,
        "minutes": None,
        "rate_snapshot": 30000,
        "amount_raw": None,
        "status": "open",
        "flags": [],
        "check_in_distance_m": 0.0,
        "check_out_distance_m": None,
    }]})

    id: int
    employee_id: int
    work_date: str
    check_in_at: str
    check_out_at: str | None
    minutes: int | None
    rate_snapshot: int
    amount_raw: float | None
    status: str
    review_reason: str | None = None
    flags: list[str]
    check_in_accuracy_m: float | None = None
    check_in_distance_m: float
    check_out_accuracy_m: float | None = None
    check_out_distance_m: float | None


class ReviewSessionOut(WorkSessionOut):
    employee_code: str
    employee_name: str


class ReviewResolvedOut(ReviewSessionOut):
    resolved_by: int | None = None
    resolved_by_name: str | None = None
    resolved_at: str | None = None
    resolved_action: str
    reason: str | None = None


class TodayOut(BaseModel):
    open_session: WorkSessionOut | None
    estimated_day_amount: int = Field(description="VND")
    paid_today: int = Field(description="VND")
    server_now: str
    checkin_cutoff: str
    can_check_in: bool


class EmployeeOut(BaseModel):
    id: int
    code: str
    full_name: str
    role: str
    telegram_id: int | None = None
    is_active: bool | None = None
    current_hourly_rate: int | None = None
    is_linked: bool | None = None
    has_open_session: bool | None = None


class WorkingNowOut(BaseModel):
    session_id: int
    employee_id: int
    code: str
    full_name: str
    check_in_at: str
    minutes_worked: int
    flags: list[str]
    check_in_distance_m: float | None = None
    check_in_accuracy_m: float | None = None
    is_outside: bool = False
    server_now: str


class PayBatchOut(BaseModel):
    id: int | None = None
    batch_id: int | None = None
    employee_id: int | None = None
    batch_no: int
    amount: int = Field(description="VND")
    approved_by: int | None = None
    approved_at: str | None = None


class PayrollSummaryOut(BaseModel):
    employee_id: int
    code: str
    full_name: str
    work_date: str
    closed_minutes: int
    eligible_minutes: int
    eligible_session_ids: list[int]
    paid_amount: int
    day_total_rounded: int
    pending_amount: int
    can_approve: bool
    unreviewed_flag_session_ids: list[int]
    hourly_rate: int | None = None
    has_open_session: bool = False
    needs_review_session_ids: list[int] = []
    pending_reason: str | None = None


class OutputSubmitOut(BaseModel):
    session_id: int
    total_kg: float
    locked_at: str | None


class ProductTotalOut(BaseModel):
    code: str
    name: str
    bags: int
    kg: float


class ReportEmployeeOut(BaseModel):
    id: int
    code: str
    full_name: str
    is_active: bool


class ReportSummaryOut(BaseModel):
    from_: date = Field(alias="from")
    to: date
    minutes: int
    salary: dict[str, int]
    paid: int
    pending: int
    pending_eligible: int
    pending_blocked: int
    needs_review_count: int
    total: int
    bags: int
    kg: float


class ReportTimeseriesOut(BaseModel):
    date: date
    minutes: int
    salary: int
    paid: int
    pending: int
    pending_eligible: int
    pending_blocked: int
    needs_review_count: int
    bags: int
    kg: float


class HistorySessionOut(WorkSessionOut):
    pay_batch_id: int | None = None
    pending_reason: str | None = None
    output: list[ProductTotalOut] = []


class HistoryDayOut(BaseModel):
    date: date
    total_amount: int
    batches: list[dict]
    unpaid_sessions: list[HistorySessionOut]


class HistoryOut(BaseModel):
    from_: date = Field(alias="from")
    to: date
    days: list[HistoryDayOut]
