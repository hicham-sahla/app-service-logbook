from typing import Iterable
from functions.utils.client import NotesClient

from functions.utils.types import (
    ErrorResponse,
    NoteAdd,
    NoteEdit,
    NoteRemove,
    SuccessResponse,
    Note,
    NoteImport,
)
from functions.utils.utils import notes_endpoint, permission_check
from ixoncdkingress.cbc.context import CbcContext


@CbcContext.expose
@notes_endpoint(NoteAdd)
def add(
    _: CbcContext,
    notes_client: NotesClient,
    model: NoteAdd,
) -> ErrorResponse[None] | SuccessResponse[Note]:
    note = notes_client.add(model)

    if isinstance(note, ErrorResponse):
        return note

    return SuccessResponse(message=f"Added Note #{note.id}", data=note)


@CbcContext.expose
@notes_endpoint()
def get(
    _: CbcContext,
    notes_client: NotesClient,
) -> SuccessResponse[Iterable[Note]]:
    return SuccessResponse(data=notes_client.get())


@CbcContext.expose
@notes_endpoint(NoteEdit)
def edit(
    context: CbcContext,
    notes_client: NotesClient,
    model: NoteEdit,
) -> ErrorResponse[None] | SuccessResponse[Note]:
    if context.user is None or not permission_check(
        context, notes_client, model.note_id
    ):
        return ErrorResponse(
            message="You do not have the rights to perform this action"
        )

    note = notes_client.edit(model)

    if isinstance(note, ErrorResponse):
        return note

    return SuccessResponse(message=f"Updated Note #{note.id}", data=note)


@CbcContext.expose
@notes_endpoint(NoteRemove)
def remove(
    context: CbcContext,
    notes_client: NotesClient,
    model: NoteRemove,
) -> ErrorResponse[None] | SuccessResponse[None]:
    if context.user is None or not permission_check(
        context, notes_client, model.note_id
    ):
        return ErrorResponse(
            message="You do not have the rights to perform this action"
        )

    error = notes_client.remove(model.note_id)

    if error is not None:
        return error

    return SuccessResponse(message="Removed Note")


@CbcContext.expose
@notes_endpoint()
def export_data(
    _: CbcContext,
    notes_client: NotesClient,
) -> SuccessResponse[Iterable[Note]]:
    """
    Returns all notes for the current agent/asset.
    """
    return SuccessResponse(data=notes_client.get())


@CbcContext.expose
@notes_endpoint(NoteImport)
def import_data(
    context: CbcContext,
    notes_client: NotesClient,
    model: NoteImport,
) -> ErrorResponse[None] | SuccessResponse[None]:
    """
    Imports all notes from a JSON file.
    """
    if context.user is None or not permission_check(context, notes_client):
        return ErrorResponse(
            message="You do not have the rights to perform this action"
        )

    notes_client.set_notes(model.notes)

    return SuccessResponse(message="Imported Notes")
