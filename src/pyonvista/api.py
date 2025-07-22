"""
A tiny API for onvista.de financial website.

The API provides at a maximum all available chart data as can be viewed on the webpage.

todo: use pydantic model instead of parsing freestyle
"""
import asyncio
import inspect
import weakref
import dataclasses
import datetime
import json as jsonlib
from typing import (
    Literal,
    Any
)
from types import SimpleNamespace

import aiohttp
from .util import make_url

ONVISTA_BASE = "https://www.onvista.de"
ONVISTA_API_BASE = "https://api.onvista.de/api/v1"

snapshot_map = {
    "FUND": "funds",
    "STOCK": "stocks",
}


@dataclasses.dataclass
class Quote:
    resolution: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    pieces: int
    instrument: "Instrument"

    @classmethod
    def from_dict(cls, instrument: "Instrument", quote:dict) -> "Quote":
        try:
            volume = int(quote["money"])
        except KeyError:
            # not stonks
            volume = int(quote["totalMoney"])
        try:
            pieces = int(quote["volume"])
        except KeyError:
            # not stonks
            pieces = int(quote['volumeBid'])

        quote= cls(
            resolution="1m",
            timestamp=datetime.datetime.strptime(quote["datetimeLast"].split(".")[0], "%Y-%m-%dT%H:%M:%S"),
            open=float(quote["open"]),
            high=float(quote["high"]),
            low=float(quote["low"]),
            close=float(quote["last"]),  # not sure if this true
            volume=volume,
            pieces=pieces,
            instrument=instrument
        )
        return quote


@dataclasses.dataclass
class Market:
    """Maps ID,market,exchange whereas exchange is acronym/key for market"""
    name: str
    code: str


@dataclasses.dataclass
class Notation:
    market: Market
    id: str


@dataclasses.dataclass(init=False)
class Instrument:
    """
    A minimal dataclass representing data from the onvista api to later request quotes

    """
    uid: str
    name: str
    symbol: str
    isin: str
    url: str
    type: str
    quote: Quote = dataclasses.field(repr=False)
    _snapshot_json: dict = dataclasses.field(repr=False)
    snapshot_valid_until: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.now, repr=False)
    notations: list[Notation] = dataclasses.field(default_factory=list)
    last_change: datetime.datetime = dataclasses.field(default_factory=datetime.datetime.now, repr=False)

    @property
    def dict(self) -> dict:
        return self._snapshot_json

    @property
    def as_tree(self) -> SimpleNamespace:
        """
        Provides a simple object tree of json for easy browsing
        """
        return jsonlib.loads(jsonlib.dumps(self._snapshot_json), object_hook=lambda d: SimpleNamespace(**d))

    @classmethod
    def from_json(cls, data: dict) -> "Instrument":
        """
        Alternate constructor to parse data to a fresh instrument instance.
        :param data: a json dict from a web response
        :return: Instrument
        """
        instrument = cls()
        instrument.notations = []
        _update_instrument(instrument, data)
        return instrument

    @classmethod
    def from_isin(cls, isin:str) -> "Instrument":
        # todo: implement
        raise NotImplementedError("Constructor not implemented yet")


def _update_instrument(instrument: Instrument, data: dict, quote: dict = None):
    """
    Updates instrument from a json data dict
    :param instrument:
    :param data:
    :return:
    """
    if data.get("expires", None):
        instrument.snapshot_valid_until = datetime.datetime.fromtimestamp(
            float(data["expires"]))
    instrument.last_change = datetime.datetime.now()
    instrument.uid = data["entityValue"]
    instrument.name = data["name"]
    instrument.isin = data.get("isin", None)
    instrument.symbol = data.get("symbol", None)
    instrument.url = data["urls"]["WEBSITE"]
    instrument.type = data["entityType"]
    if quote:
        instrument.quote = Quote.from_dict(instrument, quote)
    return instrument


def _add_notation(instrument: Instrument, notations: dict):
    """
    Ads notation to provided instrument
    :param instrument:
    :param notations:
    :return:
    """
    for notation in notations:
        market = Market(name=notation["market"]["name"], code=notation["market"]["codeExchange"])
        notation = Notation(market=market, id=notation["market"]["idNotation"])
        instrument.notations.append(notation)


class PyOnVista:
    def __init__(self):
        self._client: aiohttp.ClientSession | None = None
        self._loop: asyncio.BaseEventLoop | None = None
        self._instruments = weakref.WeakSet()

    async def install_client(self, client: Any):
        """
        This function installs the client to the pyonvista api.
        It should be called in front of any other calls to this api.
        A client must implement at least a get method and should be configured
        to follow redirects. Otherwise, you'll be warned.

        If you run an async client this function will check for a running loop. An keeps a weakref to it.
        :param client:
        :return:
        """
        if not getattr(client, "get"):
            raise AttributeError(f"Provided client {client} does not implement a get method.")

        self._client = client

        if inspect.ismethod(getattr(client, "get")):
            self._loop = weakref.ref(asyncio.get_event_loop())
        else:
            raise AttributeError(f"The provided client {client} seems not have an async get method")

    async def _get_json(self, url, *args, **kwargs) -> dict:
        """
        A wrapper avoiding boiler plate code
        :param url:
        :param args:
        :param kwargs:
        :return:
        """
        async with self._client.get(url, *args, **kwargs) as response:
            if response.status < 300:
                return dict(await response.json())

    async def search_instrument(self, key: str) -> list[Instrument]:
        url = make_url(ONVISTA_API_BASE, *["instruments", "search", "facet"], perType=10, searchValue=key)
        json = await self._get_json(url)
        facets = json["facets"]
        res = []
        for facet in facets:
            if results := facet["results"]:
                res.extend(
                    [Instrument.from_json(data) for data in results]
                )
        return res

    async def request_instrument(self, instrument: Instrument = None, isin: str = None) -> Instrument:
        """
        If instrument is provided, the instrument is updated.
        If a isin is provided a new instrument is provided.
        :param instrument:
        :param isin:
        :return:
        """
        isin = isin or instrument.isin
        if not isin:
            raise (AttributeError("At least one argument must be provided"))
        if not instrument:
            instrument = Instrument()
            instrument.isin = isin

        # is needed because not mapped propper
        type_ = snapshot_map.get(instrument.type, None)
        if not type_:
            type_ = instrument.type

        url = make_url(
            ONVISTA_API_BASE,
            type_,
            f"ISIN:{instrument.isin}"
            "/snapshot"
        )
        data = await self._get_json(url)
        if instrument:
            _update_instrument(instrument, data["instrument"], data["quote"])
        else:
            instrument = Instrument.from_json(data["instrument"])
        _add_notation(instrument, notations=data["quoteList"]["list"])
        return instrument

    async def request_quotes(
            self,
            instrument: Instrument,
            start: datetime.datetime = None,
            end: datetime.datetime = None,
            resolution: Literal["1m", "15m", "1D"] = "15m",
            notation: Notation = None,

    ) -> list[Quote]:
        """
        Gets historic quotes form on vista api.
        """
        try:
            notation = notation or instrument.notations[0]
        except IndexError:
            instrument = await self.request_instrument(instrument)
            notation = instrument.notations[0]

        start = start or datetime.datetime.now() - datetime.timedelta(days=7)
        end = end or datetime.datetime.now()+datetime.timedelta(days=1)
        request_data = make_url(
            ONVISTA_API_BASE,
            "instruments",
            str(instrument.type),
            str(instrument.uid),
            "chart_history",
            endDate=end.strftime("%Y-%m-%d"),
            idNotation=notation.id,
            resolution=resolution,
            startDate=start.strftime("%Y-%m-%d"),
        )

        data = await self._get_json(request_data)

        result = []
        if data:
            quotes = zip(
                data["datetimeLast"],
                data["first"],
                data["last"],
                data["high"],
                data["low"],
                data["volume"],
                data["numberPrices"]
            )
            for date, first, last, high, low, volume, pieces in quotes:
                result.append(
                    Quote(resolution, datetime.datetime.fromtimestamp(date), first, high, low, last, volume,
                          pieces, instrument)
                )

        return result
