import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from backend import policy


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Credentials(Input):
    email: str = Field(max_length=254)
    password: str = Field(min_length=8, max_length=64)

    @field_validator("email")
    @classmethod
    def email_value(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Некорректный email")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    role: Literal["user", "operator"]


class TokenOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class TicketCreate(Input):
    title: str = Field(description="После обрезки пробелов: 3–80 Unicode code points", json_schema_extra={"minLength": 3, "x-maxLength-after-trim": 80})
    priority: str = Field(default="normal", json_schema_extra={"enum": ["low", "normal", "high"]})

    @field_validator("title")
    @classmethod
    def title_value(cls, value):
        return policy.title_value(value)

    @field_validator("priority")
    @classmethod
    def priority_value(cls, value):
        return policy.priority_value(value)


class TicketPatch(Input):
    @staticmethod
    def patch_schema(schema):
        schema["minProperties"] = 1
        for field in schema["properties"].values():
            field.pop("default", None)

    model_config = ConfigDict(json_schema_extra=patch_schema)
    title: str | SkipJsonSchema[None] = Field(default=None, description="После обрезки пробелов: 3–80 Unicode code points", json_schema_extra={"minLength": 3, "x-maxLength-after-trim": 80})
    priority: str | SkipJsonSchema[None] = Field(default=None, json_schema_extra={"enum": ["low", "normal", "high"]})

    @field_validator("title")
    @classmethod
    def title_value(cls, value):
        if value is None:
            raise ValueError("null запрещён")
        return policy.title_value(value)

    @field_validator("priority")
    @classmethod
    def priority_value(cls, value):
        if value is None:
            raise ValueError("null запрещён")
        return policy.priority_value(value)


class StatusInput(Input):
    status: Literal["new", "active", "closed"]


class TicketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    author_id: UUID
    title: str
    priority: Literal["low", "normal", "high"]
    status: Literal["new", "active", "closed"]
    created_at: datetime


class CommentInput(Input):
    text: str = Field(description="После обрезки пробелов: 1–300 Unicode code points", json_schema_extra={"minLength": 1, "x-maxLength-after-trim": 300})

    @field_validator("text")
    @classmethod
    def text_value(cls, value):
        value = value.strip()
        if not 1 <= len(value) <= 300:
            raise ValueError("Комментарий должен содержать 1–300 символов")
        return value


class CommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    ticket_id: UUID
    author_id: UUID
    text: str
    created_at: datetime


class ErrorDetail(BaseModel):
    message: str
    request_id: str
    fields: list[dict] | None = None


class ErrorOut(BaseModel):
    error: ErrorDetail
