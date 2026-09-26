from __future__ import annotations

from abc import ABC
from typing import Any, Generic, TypeVar

from loguru import logger

from source.database import AbstractUnitOfWork

ModelType = TypeVar("ModelType")


class BaseService(ABC, Generic[ModelType]):
    """Base class for all services.

    Provides access to the Unit of Work and logging helpers.
    Does not implement CRUD operations; services own their business logic.
    """

    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self._uow: AbstractUnitOfWork = uow
        self._logger = logger.bind(service=self.__class__.__name__)

    @property
    def uow(self) -> AbstractUnitOfWork:
        """Access to Unit of Work for database operations."""
        return self._uow

    def log_operation(self, operation: str, **context: Any) -> None:
        """Log a successful operation."""
        self._logger.info(operation, **context)

    def log_error(self, operation: str, error: Exception, **context: Any) -> None:
        """Log an operation error."""
        self._logger.error(
            f"Operation failed: {operation}",
            error=str(error),
            error_type=type(error).__name__,
            **context,
        )
