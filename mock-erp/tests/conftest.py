import itertools

import pytest

import app.core.storage as storage_module


@pytest.fixture(autouse=True)
def reset_storage():
    """Give every test a fresh in-memory store and restart ERP numbering."""
    storage_module.storage.__init__()
    storage_module._ERP_SEQ = itertools.count(1)
    yield
