
import inflect
import re
from sqlalchemy.ext.declarative import declared_attr

p = inflect.engine()


def camel_to_snake(name: str) -> str:
    """Convert `CamelCase` names to `snake_case`."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


class TableNameMixin:
    @declared_attr.directive
    def __tablename__(cls) -> str:
        name = camel_to_snake(cls.__name__)
        if name.endswith("_orm"):
            name = name[:-4]
        elif name.endswith("_table"):
            name = name[:-6]
        return p.plural(name)
