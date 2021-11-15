import datetime

from pyOnvista.api import Instrument, CachedRequest, InstrumentDatabase


class Test_CacheRequest:
    def test__load_cache(self, cached_request):
        # GIVEN
        url = f"https://www.onvista.de/aktien/DE0007664039"
        # WHEN user loads the from cache
        timestamp, response = cached_request._load_cache(url)
        # THEN the response should be available from cache
        assert response
        assert timestamp.date() == datetime.date(2021, 11, 7)

    def test__dump_cache(self, response_from_cache, tmpdir):
        # GIVEN a proper response:
        response = response_from_cache
        # WHEN cached_request is taking place
        request = CachedRequest(header=dict(), path=tmpdir, validity=365)
        request._dump_cache("test", response)
        # THEN this data should be available from cache after wards
        timestamp, cached_response = request._load_cache("test")
        assert response.url == cached_response.url


class TestInstrument:
    def test_load(self, cached_request):
        # GIVEN a class
        # WHEN user
        vw = Instrument("DE0007664039", cached_request, cached_request.path, lazy_load=False)
        assert vw._loaded
        assert vw.symbol == "VOW3"
        assert vw.name == 'VOLKSWAGEN AG VZ'
        assert vw.wkn == '766403'
        assert vw.type == "Stock"
        assert vw.sector == "Kraftfahrzeugindustrie"

    def test_update(self, cached_request):
        # GIVEN a class
        # WHEN user
        vw = Instrument("DE0007664039", cached_request,cached_request.path ,lazy_load=False)
        # AND explicit updates
        vw.update()
        # THEN
        assert vw._loaded
        assert vw.symbol == "VOW3"
        assert vw.name == 'VOLKSWAGEN AG VZ'
        assert vw.wkn == '766403'
        assert vw.type == "Stock"
        assert vw.sector == "Kraftfahrzeugindustrie"

    def test_get_quotes(self, cached_request):
        # GIVEN a class
        # WHEN user instance a new instance
        vw = Instrument("DE0007664039", cached_request, cached_request.path, lazy_load=False)
        # AND selects a notation
        notation = vw.notations[0]
        # AND querys for quotes
        quotes = vw.get_quotes("month", notation)
        assert quotes


class TestInstrumentDatabase:
    def test_instruments(self, db_path):
        # GIVEN
        db = InstrumentDatabase(db_path)
        instrument = None
        # WHEN user wants to iter through database
        for instrument in db.instruments():
            assert instrument
        assert instrument.name == 'VOLKSWAGEN AG VZ'

    def test_query(self, db_path):
        # GIVEN
        db = InstrumentDatabase(db_path)
        # WHEN user queries for entry:
        instrument = db.query(isin="DE0007664039")
        # THEN
        assert instrument.name == 'VOLKSWAGEN AG VZ'
