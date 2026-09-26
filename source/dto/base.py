from pydantic import BaseModel
from pydantic import ConfigDict


class BaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
