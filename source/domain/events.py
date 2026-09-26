from dataclasses import dataclass


@dataclass(frozen=True)
class DomainEvent:
    pass


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    user_id: int
    language_code: str
