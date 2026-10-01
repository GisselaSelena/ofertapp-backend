import pytest

import app.cache
from tests.fakes import FakeRedis


@pytest.fixture(autouse=True)
def fake_redis_for_each_test(monkeypatch):
    """Keep every test isolated from a real Redis service."""
    monkeypatch.setattr(app.cache, "redis_client", FakeRedis())
