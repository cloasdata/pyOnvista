import pytest
import aiohttp
import shelve
from pathlib import Path

from pyonvista.api import PyOnVista, Instrument

INSTRUMENT_DB = Path(__file__).parent / "assets" / "instruments_for_test"

@pytest.fixture()
async def aio_client() -> aiohttp.ClientSession:
    client = aiohttp.ClientSession()
    yield client
    await client.close()


@pytest.fixture()
async def onvista_api(aio_client) -> PyOnVista:
    api = PyOnVista()
    await api.install_client(aio_client)
    return api

@pytest.fixture()
def instrument_vw() -> Instrument:
    with shelve.open(str(INSTRUMENT_DB)) as db:
        return db["DE0007664039"]

@pytest.fixture()
def instrument_etf() -> Instrument:
    with shelve.open(str(INSTRUMENT_DB)) as db:
        return db['IE00B42NKQ00']
