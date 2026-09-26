from sqlalchemy import Select

from source.database.models import UserOrm
from source.enums import UserRole
from .base import Specification


class UserRoleSpec(Specification):
    def __init__(self, role: UserRole) -> None:
        self.role = role

    def apply(self, query: Select) -> Select:
        return query.where(UserOrm.role == self.role)
