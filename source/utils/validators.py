import re


def validate_age(value: str, min_age: int = 1, max_age: int = 120) -> int:
    if not value.isdigit():
        raise ValueError("Age must be a number")
    age = int(value)
    if not (min_age <= age <= max_age):
        raise ValueError(f"Age must be between {min_age} and {max_age}")
    return age


def validate_phone(value: str) -> str:
    pattern = re.compile(r"^\+?[1-9]\d{1,14}$")
    if not pattern.match(value):
        raise ValueError("Invalid phone number format")
    return value
