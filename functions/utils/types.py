import time
from typing import Annotated, Generic, TypeVar, List

from bson.objectid import ObjectId
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

T = TypeVar("T")

JSONObjectId = Annotated[
    ObjectId, PlainSerializer(lambda x: str(x), return_type=str, when_used="json")
]


class StackReplacement(BaseModel):
    stack_identifier: str
    removed_serial_number: str | None = Field(default=None)
    added_serial_number: str | None = Field(default=None)


class Note(BaseModel):
    id: JSONObjectId = Field(
        default_factory=ObjectId, alias="_id", serialization_alias="_id"
    )
    user: str | None = Field(default=None, deprecated=True)
    text: str
    created_on: int = Field(default_factory=lambda: round(time.time() * 1000))

    author_id: str | None = Field(default=None)
    author_name: str | None = Field(default=None)

    editor_id: str | None = Field(default=None)
    editor_name: str | None = Field(default=None)
    updated_on: int | None = Field(default=None)

    subject: str | None = Field(default=None)
    category: int | None = Field(default=None)
    note_category: str | None = Field(default=None)

    # Daily report
    additional_user: str | None = Field(default=None)
    performed_on: int | None = Field(default=None)
    week_number: int | None = Field(default=None)
    worked_hours: int | None = Field(default=None)
    mcps_worked_on: str | None = Field(default=None)
    fcps_worked_on: str | None = Field(default=None)
    owls_worked_on: str | None = Field(default=None)

    # Calibrations
    tag_number: str | None = Field(default=None)

    # Software changes

    # Stack replacements
    stack_replacements: List[StackReplacement] | None = Field(default=None)

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

    subject: str | None = Field(default=None)
    category: int | None = Field(default=None)
    note_category: str | None = Field(default=None)

    # Daily report
    additional_user: str | None = Field(default=None)
    performed_on: int | None = Field(default=None)
    week_number: int | None = Field(default=None)
    worked_hours: int | None = Field(default=None)
    mcps_worked_on: str | None = Field(default=None)
    fcps_worked_on: str | None = Field(default=None)
    owls_worked_on: str | None = Field(default=None)

    # Calibrations
    tag_number: str | None = Field(default=None)

    # Software changes

    # Stack replacements
    stack_replacements: List[StackReplacement] | None = Field(default=None)


class NoteAdd(BaseModel):
    text: str

    subject: str | None = Field(default=None)
    category: int | None = Field(default=None)
    note_category: str | None = Field(default=None)

    # Daily report
    additional_user: str | None = Field(default=None)
    performed_on: int | None = Field(default=None)
    week_number: int | None = Field(default=None)
    worked_hours: int | None = Field(default=None)
    mcps_worked_on: str | None = Field(default=None)
    fcps_worked_on: str | None = Field(default=None)
    owls_worked_on: str | None = Field(default=None)

    # Settings change
    # Calibrations
    tag_number: str | None = Field(default=None)

    # Software changes no additional fields

    # Stack replacements
    stack_replacements: List[StackReplacement] | None = Field(default=None)


class NoteRemove(BaseModel):
    note_id: str


class NoteImport(BaseModel):
    notes: List[Note]
