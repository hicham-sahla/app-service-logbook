import time
from typing import Annotated, Generic, TypeVar
from pydantic import BaseModel, ConfigDict, Field, PlainSerializer
from bson.objectid import ObjectId

T = TypeVar('T')

JSONObjectId = Annotated[
    ObjectId, PlainSerializer(lambda x: str(x), return_type=str, when_used='json')
]

class Note(BaseModel):
    id: JSONObjectId = Field(default_factory=ObjectId, alias='_id', serialization_alias='_id')
    user: str
    text: str
    created_on: int = Field(default_factory=lambda: round(time.time()*1000))

    model_config = ConfigDict(arbitrary_types_allowed=True)

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

class NoteAdd(BaseModel):
    text: str

class NoteRemove(BaseModel):
    note_id: str
