from typing import Tuple, Dict
from unittest.mock import Mock

import pytest

from gmail.main import GmailService


@pytest.fixture
def gmail_service_with_mocks(simple_db) -> Tuple[GmailService, Dict[str, Mock]]:
    """
    Provide a GmailService instance with core dependencies mocked for unit tests.
    Returns a tuple of (service, mocks_dict).
    """
    service = GmailService(db_path=simple_db.db_path)

    mocks: Dict[str, Mock] = {
        "gmail_api": Mock(),
        "storage": Mock(),
        "config": Mock(),
        "db": Mock(),
        "summarizer": Mock(),
    }

    # Attach mocks to the service
    service.gmail_api = mocks["gmail_api"]
    service.storage = mocks["storage"]
    service.config = mocks["config"]
    service.db = mocks["db"]
    service.summarizer = mocks["summarizer"]

    return service, mocks

