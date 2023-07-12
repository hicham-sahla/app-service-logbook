from functions.utils.client import NotesClient

from functions.utils.types import ErrorResponse, NoteAdd, NoteEdit, NoteRemove, SuccessResponse
from functions.utils.utils import notes_endpoint
from ixoncdkingress.cbc.context import CbcContext

@notes_endpoint(NoteAdd)
def add(_, notes_client: NotesClient, model: NoteAdd):
    note = notes_client.add(model.text)

    if isinstance(note, ErrorResponse):
        return note

    return SuccessResponse(message=f'Added Note #{note.id}', data=note)

@notes_endpoint()
def get(_, notes_client: NotesClient):

    return SuccessResponse(data=notes_client.get())

@notes_endpoint(NoteEdit)
def edit(_, notes_client: NotesClient, model: NoteEdit):
    note = notes_client.edit(model.text, model.note_id)

    if isinstance(note, ErrorResponse):
        return note

    return SuccessResponse(message=f'Updated Note #{note.id}', data=note)

@notes_endpoint(NoteRemove)
def remove(context: CbcContext, notes_client: NotesClient, model: NoteRemove):
    if context.user is None:
            return ErrorResponse(message='Note not removed')

    error = notes_client.remove(model.note_id, context.user.public_id)

    if error is not None:
        return error

    return SuccessResponse(message=f'Removed Note')
