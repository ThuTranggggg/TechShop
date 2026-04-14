"""
Pytest Configuration and Fixtures

Common fixtures for all payment tests.
"""

import os
import django
import pytest
from django.conf import settings

# Setup Django for testing
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test.utils import setup_test_environment, teardown_test_environment
from django.db import connection
from django.db.backends.base.base import BaseDatabaseWrapper


@pytest.fixture(scope="session")
def django_setup():
    """Setup Django test environment"""
    setup_test_environment()
    yield
    teardown_test_environment()


@pytest.fixture(scope="session")
def db_setup(django_setup):
    """Setup test database"""
    connection.ensure_connection()
    with connection.schema_editor() as schema_editor:
        # Create tables if needed
        pass
    yield
    # Teardown


@pytest.fixture
def mock_payment_repo():
    """Mock payment repository"""
    from unittest.mock import Mock
    return Mock()


@pytest.fixture
def mock_provider_factory():
    """Mock provider factory"""
    from unittest.mock import Mock
    return Mock()
