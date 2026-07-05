import pytest

from worldstate import SqliteWorldStore


@pytest.fixture()
def store():
    s = SqliteWorldStore.open(":memory:")
    try:
        yield s
    finally:
        s.close()
