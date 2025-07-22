import shelve

import pytest

from src.pyonvista.api import PyOnVista, Instrument
from conftest import INSTRUMENT_DB


class TestPyOnVista:
    def test_init(self):
        api = PyOnVista()
        assert api

    @pytest.mark.asyncio
    async def test_install_client(self, aio_client):
        api = PyOnVista()
        await api.install_client(aio_client)
        assert api._client == aio_client

    @pytest.mark.asyncio
    async def test_search_instrument(self, onvista_api, aio_client):
        async with aio_client:
            instrument = (await onvista_api.search_instrument("vw"))[0]
        assert instrument.name == "Volkswagen (VW) Vz"
        # update instrument test db here
        with shelve.open(str(INSTRUMENT_DB)) as db:
            db[instrument.isin] = instrument

    @pytest.mark.asyncio
    async def test_request_instrument(self, onvista_api, aio_client, instrument_vw):
        async with aio_client:
            await onvista_api.request_instrument(instrument_vw)
        assert instrument_vw.quote

    @pytest.mark.asyncio
    async def test_search_etf(self, onvista_api, aio_client):
        async with aio_client:
            instrument = (await onvista_api.search_instrument("IE00B42NKQ00"))[0]
        assert instrument.uid == "99206463"
        # update instrument test db here
        with shelve.open(str(INSTRUMENT_DB)) as db:
            db[instrument.isin] = instrument

    @pytest.mark.asyncio
    async def test_request_quotes(self, onvista_api: PyOnVista, instrument_vw, aio_client):
        async with aio_client:
            quotes = await onvista_api.request_quotes(instrument_vw)
        assert quotes

    @pytest.mark.asyncio
    async def test_request_quotes_etf(self, onvista_api: PyOnVista, instrument_etf, aio_client):
        async with aio_client:
            quotes = await onvista_api.request_quotes(instrument_etf)
        assert quotes
