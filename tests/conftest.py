import pytest

from tests.factories import BuildFactory, NightfarerFactory, UserFactory


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def nightfarer(db):
    return NightfarerFactory()


@pytest.fixture
def build(db):
    return BuildFactory()


@pytest.fixture(autouse=True)
def plain_static_storage(settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
