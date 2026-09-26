from abc import ABC
from abc import abstractmethod
from sqlalchemy import Select


class Specification(ABC):
    @abstractmethod
    def apply(self, query: Select) -> Select:
        raise NotImplementedError
