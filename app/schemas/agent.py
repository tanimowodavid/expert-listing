import re
import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class AgentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=100)]
    email: EmailStr
    phone: Annotated[str, Field(pattern=r"^\+?\d{7,15}$")]

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, value: object) -> object:
        if isinstance(value, str):
            return re.sub(r"[\s\-()]", "", value)
        return value


class AgentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str
    phone: str
    created_at: datetime