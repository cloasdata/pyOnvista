
from src.pyonvista.api import Instrument


class TestInstrument:
    def test_init(self):
        instrument = Instrument()
        assert instrument
