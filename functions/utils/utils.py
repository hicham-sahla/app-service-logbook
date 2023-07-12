from typing import Callable, Optional

from pydantic import BaseModel, ValidationError
from functions.utils.client import NotesClient

from functions.utils.types import ErrorResponse, Response
from ixoncdkingress.cbc.context import CbcContext

def parse_arguments(parse_func: Callable[..., BaseModel]):
    """"
    Takes the given kwargs of the function (except for the CbcContext) and parses them into a
    pydantic model and adds this to the new function by giving a kwarg `model` with the new pydantic
    model. Can also be used with a normal function rather than a pydantic model.

    Example:
    In order to typecheck this:
    ```python
    def add(context: CbcContext, note_id: str, text: str):
    ```

    We can use this:
    ```python
    @parse_arguments(NoteEdit)
    def add(context: CbcContext, model: NoteEdit):
        assert model.note_id and model.text
    ```

    Which actually works like this:
    ```python
    @parse_arguments(lambda note_id, text: NoteEdit(note_id=note_id, text=text))
    def add(context: CbcContext, model: NoteEdit):
        assert model.note_id and model.text
    ```
    """

    def decorator(func):
        def wrapper(context: CbcContext,**func_args):
            try:
                return func(context, model=parse_func(**func_args))
            except ValidationError as e:
                return ErrorResponse(data=e.errors(), message='Exception parsing input')
        return wrapper

    return decorator

def json_response(func: Callable[..., Response]):
    """
    Ensures that a function that returns a pydantic `Response` object is turned into a JSON
    serializable object.
    """

    def wrapper(*args,**kwargs):
        return func(*args, **kwargs).model_dump(mode='json', by_alias=True)
    return wrapper

def notes_endpoint(parse_func: Optional[Callable[..., BaseModel]] = None):
    """
    Merges the functionality of `json_response`, `parse_arguments` and injects the notes client
    into the given function. When a parse function is given the kwargs `notes_client` and `model`
    will both be set. Without a parse function only the `notes_client` is set.

    Example:
    ```python
    @notes_endpoint(NoteAdd)
    def add(context: CbcContext, notes_client: NotesClient, model: NoteAdd):
    ````
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return json_response(
                    parse_arguments(parse_func)(
                        NotesClient.inject(func)
                    ) if parse_func else NotesClient.inject(func)
                )(*args, **kwargs)
            except BaseException as e:
                return ErrorResponse(data=str(e)).model_dump(by_alias=True)
        return wrapper
    return decorator
