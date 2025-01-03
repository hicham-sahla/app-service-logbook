import time
from functools import reduce
from operator import add
from typing import Any, Iterable

from bson.objectid import ObjectId
from ixoncdkingress.cbc.context import CbcContext
from ixoncdkingress.cbc.document_db_client import DocumentDBClient

from functions.utils.types import ErrorResponse, Note


class NotesClient:
    document_client: DocumentDBClient

    @classmethod
    def inject(cls, func):
        """
        Automatically injects a kwarg `notes_client` into the given function. The given function
        needs to have an argument `context: CbcContext`.

        Automatically returns an error response when either the agent/asset or user are not set.
        """

        def wrapper(context: CbcContext, *args ,**kwargs):
            if (
                not context.user
                or not (context.agent or context.asset)
                or not context.document_db_client
            ):
                return ErrorResponse(message='Agent/Asset, user and DB configuration are required')

            client = cls(
                context.document_db_client,
                context.user.public_id,
                context.user.name,
                context.agent_or_asset.public_id,
                context.agent.public_id if context.agent else None
            )

            return func(context, notes_client=client, *args, **kwargs)
        return wrapper

    def __init__(
            self,
            document_client: DocumentDBClient,
            user_id: str,
            user_name: str,
            agent_or_asset_id: str,
            agent_id: str | None,
        ) -> None:
        self.user_id = user_id
        self.user_name = user_name
        self.agent_or_asset_id = agent_or_asset_id
        self.document_client = document_client

        self.in_id_filtermap = {
            'agent_or_asset_id': {
                '$in': [idx for idx in {self.agent_or_asset_id, agent_id} if idx]
            }
        }

        agent_or_asset = self.document_client.find_one(filter_map={
            'agent_or_asset_id': agent_or_asset_id
        })

        if agent_or_asset is None:
            self.document_client.insert_one({
                'agent_or_asset_id': agent_or_asset_id,
                'notes': []
            })

    def add(self, text: str) -> Note | ErrorResponse:
        note = Note(
            text=text,
            author_id=self.user_id,
            author_name=self.user_name,
        )

        result = self.document_client.update_one(
            {'agent_or_asset_id': self.agent_or_asset_id},
            {'$push': {'notes': note.model_dump(by_alias=True)}}
        )

        if result.modified_count == 0:
            return ErrorResponse(message='Note not added')

        return note

    def get(self) -> Iterable[Note]:
        documents: Iterable[dict[str, Any]] = self.document_client.find(self.in_id_filtermap) or []

        return sorted(
            reduce(add, [
                [
                    Note(**{
                        **note,
                        "author_id": (note.get("author_id") or note.get("user")), # Backwards compatability with old messages
                        "user": (note.get("author_id") or note.get("user")), # Backwards compatability with new messages
                    })
                    for note in document.get('notes', [])
                ]
                for document in documents
            ]),
            key=lambda note: note.created_on,
            reverse=True
        )

    def edit(self, text: str, note_id: str) -> Note | ErrorResponse:
        result = self.document_client.update_many(
            {**self.in_id_filtermap, 'notes._id': ObjectId(note_id)},
            {'$set': {
                'notes.$.text': text,
                'notes.$.editor_id': self.user_id,
                'notes.$.editor_name': self.user_name,
                'notes.$.updated_on': round(time.time() * 1000),
            }}
        )

        note = self.find_one_note(note_id)

        if result.modified_count == 0 or not note:
            return ErrorResponse(message='Note not modified')

        return note

    def remove(self, note_id: str, user_id: str) -> ErrorResponse | None:
        result = self.document_client.update_many(
            {
                **self.in_id_filtermap,
                '$or': [
                    {'notes.user': user_id}, # Backwards compatability with old messages
                    {'notes.author_id': user_id}, # Compatability with new messages
                ]
            },
            {'$pull': {'notes': {'_id': ObjectId(note_id)}}}
        )

        if result.modified_count == 0:
            return ErrorResponse(message='Note not removed')
        return None

    def find_one_note(self, note_id: str) -> Note | None:
        note = (self.document_client.find_one(
            projection={'notes': {'$elemMatch': {'_id': ObjectId(note_id)}}},
            filter_map=self.in_id_filtermap
        ) or {}).get('notes', [None]).pop()

        return Note(**note) if note else note
