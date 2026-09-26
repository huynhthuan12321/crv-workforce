from enum import StrEnum


class EmployeeRole(StrEnum):
    employee = "employee"
    manager = "manager"
    director = "director"


class SessionStatus(StrEnum):
    open = "open"
    closed = "closed"
    needs_review = "needs_review"


class OutboxStatus(StrEnum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
