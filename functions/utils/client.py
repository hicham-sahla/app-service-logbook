from typing import Iterable
from ixoncdkingress.cbc.context import CbcContext
from ixoncdkingress.cbc.document_db_client import DocumentDBClient
from functions.utils.types import ErrorResponse, Note
from bson.objectid import ObjectId

class NotesClient:
    document_client: DocumentDBClient

    @classmethod
    def inject(cls, func):
        """
        Automatically injects a kwarg `notes_client` into the given function. The given function
        needs to have an argument `context: CbcContext`.

        Automatically returns an error response when either the agent or user are not set.
        """

        def wrapper(context: CbcContext, *args ,**kwargs):
            if not context.user or not context.agent or not context.document_db_client:
                return ErrorResponse(message='Agent, user and DB configuration are required')

            client = cls(context.document_db_client, context.user.public_id, context.agent.public_id)

            return func(context, notes_client=client, *args, **kwargs)
        return wrapper

    def __init__(self, document_client: DocumentDBClient, user_id: str, agent_id: str) -> None:
        self.user_id = user_id
        self.agent_id = agent_id
        self.document_client = document_client

        agent = self.document_client.find_one(filter_map={
            'agent_id': agent_id
        })

        if agent is None:
            self.document_client.insert_one({
                'agent_id': agent_id,
                'notes': []
            })

    def add(self, text: str) -> Note | ErrorResponse:
        note = Note(
            user=self.user_id,
            text=text,
        )

        result = self.document_client.update_one(
            {'agent_id': self.agent_id},
            {'$push': {'notes': note.model_dump(by_alias=True)}}
        )

        if result.modified_count == 0:
            return ErrorResponse(message='Note not added')

        return note

    def get(self) -> Iterable[Note]:
        document = self.document_client.find_one(
            filter_map={'agent_id': self.agent_id }
        ) or {}

        return [Note(**note) for note in reversed(document.get('notes', []))]

    def edit(self, text: str, note_id: str) -> Note | ErrorResponse:
        result = self.document_client.update_one(
            {'agent_id': self.agent_id, 'notes._id': ObjectId(note_id)},
            {'$set': {'notes.$.text': text}}
        )

        note = self._find_one_note(note_id)

        if result.modified_count == 0 or not note:
            return ErrorResponse(message='Note not modified')

        return note

    def remove(self, note_id: str, user_id: str) -> ErrorResponse | None:
        result = self.document_client.update_one(
            {'agent_id': self.agent_id, 'notes.user': user_id},
            {'$pull': {'notes': { '_id': ObjectId(note_id) }}}
        )

        if result.modified_count == 0:
            return ErrorResponse(message='Note not removed')
        return None

    def _find_one_note(self, note_id: str) -> Note | None:
        note = (self.document_client.find_one(
            projection={'notes': {'$elemMatch': { '_id': ObjectId(note_id) }}},
            filter_map={'agent_id': self.agent_id}
        ) or {}).get('notes', [None]).pop()

        return Note(**note) if note else note
