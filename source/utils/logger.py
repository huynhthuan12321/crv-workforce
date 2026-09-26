import logging
import sys

from loguru import logger

from source.constants import LoggingConfig


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level_name = record.levelname

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level_name,
            record.getMessage(),
        )


class LoggingConfigurator:
    def __init__(self, config: LoggingConfig) -> None:
        self.config = config
        self.logger = logger

    def _is_user_message(self, message: str) -> bool:
        return (
            self.config.USER_MESSAGE_MARKER_START in message
            and self.config.USER_MESSAGE_MARKER_END in message
        )

    def _console_filter(self, record: dict) -> bool:
        if self._is_user_message(record["message"]):
            return self.config.CONSOLE_MESSAGE
        return True

    def _file_filter(self, record: dict) -> bool:
        if self._is_user_message(record["message"]):
            return self.config.FILE_MESSAGE
        return True

    def _setup_loguru_basics(self) -> None:
        self.logger.remove()
        self.logger.level("DEBUG", color="<bold><white>")
        self.logger.level("INFO", color="<bold><light-green>")
        self.logger.level("WARNING", color="<bold><yellow>")
        self.logger.level("ERROR", color="<bold><red>")
        self.logger.level("CRITICAL", color="<bold><light-red>")

        logging.basicConfig(
            handlers=[InterceptHandler()],
            level=logging.DEBUG,
            force=True,
        )
        self.logger.debug("Standard logging intercepted successfully.")

    def _add_console_handler(self) -> None:
        self.logger.add(
            sys.stderr,
            format=self.config.CONSOLE_LOG_FORMAT,
            level=self.config.CONSOLE_LEVEL.upper(),
            colorize=True,
            filter=self._console_filter,
        )
        self.logger.debug("Console handler added.")

    def _add_file_handlers(self) -> None:
        common_file_args = {
            "format": self.config.FILE_LOG_FORMAT,
            "rotation": self.config.FILE_ROTATION,
            "retention": self.config.FILE_RETENTION,
            "compression": self.config.FILE_COMPRESSION,
            "encoding": "utf-8",
            "mode": "a",
            "colorize": False,
            "enqueue": True,
            "backtrace": True,
            "diagnose": True,
            "filter": self._file_filter,
        }
        log_file_name = "{time:YYYY-MM-DD}.log"

        if self.config.FILE_ERROR:
            self.config.ERROR_LOG_DIR.mkdir(parents=True, exist_ok=True)
            error_log_path = self.config.ERROR_LOG_DIR / log_file_name

            self.logger.add(error_log_path, level="ERROR", **common_file_args)
            self.logger.debug("Error file handler added.")

        if self.config.FILE_FULL:
            self.config.FULL_LOG_DIR.mkdir(parents=True, exist_ok=True)
            full_log_path = self.config.FULL_LOG_DIR / log_file_name

            self.logger.add(
                full_log_path,
                level=self.config.FILE_LEVEL.upper(),
                **common_file_args,
            )
            self.logger.debug("Full file handler added.")

    def configure_logging(self) -> None:
        self._setup_loguru_basics()
        self._add_console_handler()
        self._add_file_handlers()
        self.logger.info("Logging setup complete.")


def setup_logger() -> None:
    configurator = LoggingConfigurator(LoggingConfig())
    configurator.configure_logging()
