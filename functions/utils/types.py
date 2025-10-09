import time
from typing import Annotated, Generic, TypeVar
from bson.objectid import ObjectId
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

T = TypeVar("T")

JSONObjectId = Annotated[
    ObjectId, PlainSerializer(lambda x: str(x), return_type=str, when_used="json")
]


class Note(BaseModel):
    id: JSONObjectId = Field(
        default_factory=ObjectId, alias="_id", serialization_alias="_id"
    )
    user: str | None = Field(default=None, deprecated=True)
    text: str
    external_note: bool | None = Field(default=None)
    created_on: int = Field(default_factory=lambda: round(time.time() * 1000))

    author_id: str | None = Field(default=None)
    author_name: str | None = Field(default=None)

    editor_id: str | None = Field(default=None)
    editor_name: str | None = Field(default=None)
    updated_on: int | None = Field(default=None)

    subject: str | None = Field(default=None)
    category: int | None = Field(default=None)
    note_category: str | None = Field(default=None)

    performed_on: int | None = Field(default=None)

    # Calibrations
    tag_number: str | None = Field(default=None)

    # Software changes

    # Stack replacements
    stack_replacements: str | None = Field(default=None)
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="ignore")


class Response(BaseModel, Generic[T]):
    data: T | None = Field(default=None)
    message: str | None = Field(default=None)
    success: bool = Field(default=True)


class SuccessResponse(Response[T]):
    success: bool = Field(default=True)


class ErrorResponse(Response[T]):
    message: str = Field(default="An unexpected error occurred")
    success: bool = Field(default=False)


class NoteEdit(BaseModel):
    note_id: str
    text: str
    external_note: bool | None = Field(default=None)
    subject: str | None = Field(default=None)
    category: int | None = Field(default=None)
    note_category: str | None = Field(default=None)

    performed_on: int | None = Field(default=None)

    # Calibrations
    tag_number: str | None = Field(default=None)

    # Software changes

    # Stack replacements
    stack_replacements: str | None = Field(default=None)


class NoteAdd(BaseModel):
    text: str
    external_note: bool | None = Field(default=None)
    subject: str | None = Field(default=None)
    category: int | None = Field(default=None)
    note_category: str | None = Field(default=None)

    # Date field for moment of action
    performed_on: int | None = Field(default=None)

    # Settings change
    # Calibrations
    tag_number: str | None = Field(default=None)

    # Software changes no additional fields

    # Stack replacements
    stack_replacements: str | None = Field(default=None)


class NoteRemove(BaseModel):
    note_id: str


class NoteImport(BaseModel):
    notes: List[Note]
