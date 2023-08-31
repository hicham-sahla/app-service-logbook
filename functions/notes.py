from functions.utils.client import NotesClient

from functions.utils.types import ErrorResponse, NoteAdd, NoteEdit, NoteRemove, SuccessResponse
from functions.utils.utils import notes_endpoint, permission_check
from ixoncdkingress.cbc.context import CbcContext

@CbcContext.expose
@notes_endpoint(NoteAdd)
def add(_, notes_client: NotesClient, model: NoteAdd):
    note = notes_client.add(model.text)

    if isinstance(note, ErrorResponse):
        return note

    return SuccessResponse(message=f'Added Note #{note.id}', data=note)

@CbcContext.expose
@notes_endpoint()
def get(_, notes_client: NotesClient):

    return SuccessResponse(data=notes_client.get())

@CbcContext.expose
@notes_endpoint(NoteEdit)
def edit(context: CbcContext, notes_client: NotesClient, model: NoteEdit):
    if context.user is None or not permission_check(context, notes_client, model.note_id):
         return ErrorResponse(message='You do not have the rights to perform this action')

    note = notes_client.edit(model.text, model.note_id)

    if isinstance(note, ErrorResponse):
        return note

    return SuccessResponse(message=f'Updated Note #{note.id}', data=note)

@CbcContext.expose
@notes_endpoint(NoteRemove)
def remove(context: CbcContext, notes_client: NotesClient, model: NoteRemove):
    if context.user is None or not permission_check(context, notes_client, model.note_id):
         return ErrorResponse(message='You do not have the rights to perform this action')

    error = notes_client.remove(model.note_id, context.user.public_id)

    if error is not None:
        return error

    return SuccessResponse(message='Removed Note')
