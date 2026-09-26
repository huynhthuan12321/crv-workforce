from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoggingConfig:
    CONSOLE_LEVEL: str = "INFO"
    FILE_LEVEL: str = "DEBUG"
    CONSOLE_MESSAGE: bool = True
    FILE_MESSAGE: bool = True
    FILE_FULL: bool = True
    FILE_ERROR: bool = True
    FILE_ROTATION: str = "100 MB"
    FILE_RETENTION: str = "30 days"
    FILE_COMPRESSION: str = "zip"

    BASE_LOG_DIR: Path = Path("source") / "data"
    ERROR_LOG_DIR: Path = Path("source") / "data" / "error_logs"
    FULL_LOG_DIR: Path = Path("source") / "data" / "full_logs"

    CONSOLE_LOG_FORMAT: str = (
        "<blue>{time:YYYY-MM-DD HH:mm:ss.SSS}</blue> <white>|</white> "
        "<level>{level: <8}</level> <white>|</white> "
        "<light-blue>{name}</light-blue>:<light-blue>{function}</light-blue>:"
        "<light-blue>{line}</light-blue> <white>-</white> <level>{message}</level>"
    )
    FILE_LOG_FORMAT: str = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
        "{name}:{function}:{line} - {message}"
    )

    USER_MESSAGE_MARKER_START: str = "Update id="
    USER_MESSAGE_MARKER_END: str = "is handled."
