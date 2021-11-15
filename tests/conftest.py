import pytest

from pyOnvista import CachedRequest


@pytest.fixture(scope="session")
def db_path() -> str:
    return "DE0007664039_1/"


@pytest.fixture(scope="session")
def cache_validity():
    return 365


@pytest.fixture(scope="session")
def cached_request(db_path, cache_validity):
    return CachedRequest(header=dict(), path=db_path, validity=cache_validity)

@pytest.fixture()
def response_from_cache(cached_request):
    url = f"https://www.onvista.de/aktien/DE0007664039"
    timestamp, response = cached_request._load_cache(url)
    return response