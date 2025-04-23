import os
from typing import Any, Iterable
from unittest.mock import MagicMock
from ixoncdkingress.function.api_client import ApiClient
from ixoncdkingress.function.context import FunctionContext, FunctionResource
from pymongo import MongoClient
import pytest

import functions
import functions.utils
import functions.utils.client
import functions.utils.types


@pytest.fixture
def mongo_conn_setup() -> Iterable[MongoClient[Any]]:
    yield MongoClient(
        "mongodb://{}:{}/{}".format(
            os.environ.get("UNIT_TEST_MONGO_HOST", "0.0.0.0"),
            int(os.environ.get("UNIT_TEST_MONGO_PORT", "23221")),
            os.environ.get("UNIT_TEST_MONGO_NAME", "admin"),
        ),
        tz_aware=True,
        connect=False,
        # Other optional parameters can be passed as keyword arguments:
        maxIdleTimeMS=60000,
        serverSelectionTimeoutMs=4000,
        # Authentication:
        username=os.environ.get("UNIT_TEST_MONGO_USER", "root"),
        password=os.environ.get("UNIT_TEST_MONGO_PASS", "mongo-root"),
        # TLS/SSL configuration:
        tls=False,
    )


@pytest.fixture
def mongo_client(mongo_conn_setup: MongoClient[Any]) -> Iterable[MongoClient[Any]]:
    client = mongo_conn_setup
    client.get_database("admin").command("dropAllRolesFromDatabase")

    for dbn in client.list_database_names():
        if dbn in {"admin", "local", "config"}:
            continue

        client.drop_database(dbn)

    yield client

    for dbn in client.list_database_names():
        if dbn in {"admin", "local", "config"}:
            continue

        client.drop_database(dbn)


@pytest.fixture
def api_client() -> MagicMock:
    return MagicMock(name="api_client", spec=ApiClient)


@pytest.fixture
def user() -> FunctionResource:
    return FunctionResource(
        public_id="user00000000",
        name="test_user",
        custom_properties={},
        permissions=None,
    )


@pytest.fixture
def company() -> FunctionResource:
    return FunctionResource(
        public_id="company00000",
        name="test_company",
        custom_properties={},
        permissions=None,
    )


@pytest.fixture
def asset() -> FunctionResource:
    return FunctionResource(
        public_id="asset0000000",
        name="test_asset",
        custom_properties={},
        permissions=None,
    )


@pytest.fixture
def agent() -> FunctionResource:
    return FunctionResource(
        public_id="agent0000000",
        name="test_agent",
        custom_properties={},
        permissions=None,
    )


@pytest.fixture
def template() -> FunctionResource:
    return FunctionResource(
        public_id="template0000",
        name="test_template",
        custom_properties={},
        permissions=None,
    )


@pytest.fixture
def config() -> dict[str, str]:
    return {}


@pytest.fixture
def function_context(
    config: dict[str, str],
    api_client: MagicMock,
    mongo_client: MongoClient[Any],
    user: FunctionResource,
    company: FunctionResource,
    asset: FunctionResource,
    agent: FunctionResource,
    template: FunctionResource,
) -> FunctionContext:
    return FunctionContext(
        config=config,
        api_client=api_client,
        mongo_client=mongo_client,
        user=user,
        company=company,
        asset=asset,
        agent=agent,
        template=template,
        document_db_collection_name="test_collection",
    )


def set_time(time: float) -> None:
    pytest.MonkeyPatch().setattr(functions.utils.types.time, "time", lambda: time)  # type: ignore[attr-defined]
    pytest.MonkeyPatch().setattr(functions.utils.client.time, "time", lambda: time)  # type: ignore[attr-defined]
