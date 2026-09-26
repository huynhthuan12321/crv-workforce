from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageCode:
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) != 2:
            raise ValueError("Language code must be a 2-letter string")
