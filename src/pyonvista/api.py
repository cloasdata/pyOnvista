"""
A tiny API for onvista.de financial website.

The API provides at a maximum all available chart data as can be viewed on the webpage.

The API core uses package requests to download contents.
The implementation of requests is very flat without deeper exception handling.

It uses the super fast lxml binding to C libxml2 and libxslt instead of beautiful soup
for html parsing. xpath are hardcoded but may be user defined at a later stage.
"""
import datetime
import dataclasses
import functools
import hashlib
from pathlib import Path
import pickle
import typing
import json
import requests
import shelve
from operator import itemgetter

from requests import Response, Request
from lxml.html import fromstring, HtmlElement
import httpx
# todo add support for historic values

FP_MARKETS = Path(__file__).parent / "inc/markets.json"

# [timestamp,"open", "high", "low", "close", "volume"]
get_timestamp = itemgetter(0)
get_open = itemgetter(1)
get_high = itemgetter(2)
get_low = itemgetter(3)
get_close = itemgetter(4)
get_volume = itemgetter(5)

tab_dict = {
    "week": "T5",
    "month": "M1",
    "year": "J1",
    "all": "MAX"
}


@dataclasses.dataclass
class InstrumentQuote:
    resolution: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclasses.dataclass
class Notation:
    """Maps ID,market,exchange whereas exchange is acronym/key for market"""
    id: str
    market: str
    exchange: str = None


class Request:
    def __init__(self, header: dict):
        self._header = header
        self._response = None

    @property
    def header(self):
        return self._header

    @property
    def response(self) -> typing.Optional[Response]:
        return self._response

    def __call__(self, url: str) -> Response:
        return self.request(url)

    def request(self, url: str) -> Response:
        """
        Simple downloader which uses requests get method.
        raises http error

        :param url: An url to any website. The hash of the url is used as key for the cache.
        :return: tuple(response, status)
        """
        self._response = requests.get(
            url=url,
            headers=self._header.pop("headers", None),
            proxies=self._header.pop("proxies", None),
            timeout=self._header.pop("timeout", None)
        )
        if self._response.status_code >= 400:
            raise requests.exceptions.HTTPError(self._response.status_code)
        else:
            return self._response


class CachedRequest(Request):
    """
    Wraps requests get method. If cache is configured class tries to query the cache. If no response is found
    it fires the http get to onvista.de
    The cache is highly recommended to avoid any abusing.
    """

    def __init__(self, header: dict, path: str|Path, validity: int):
        super().__init__(header)
        self._validity = validity
        self._path = path
        self._header = header if header else dict()

    @property
    def path(self):
        return self._path

    def _load_cache(self, url: str) -> tuple[typing.Optional[datetime.datetime], typing.Optional[requests.Response]]:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        path = Path(self._path) / url_hash[:2] / url_hash[2:]
        if path.exists():
            with open(path, "rb") as pickle_file:
                return pickle.load(pickle_file)
        else:
            return None, None

    def _dump_cache(self, url: str, response: requests.Response):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        path = Path(self._path) / url_hash[:2]
        path.mkdir(exist_ok=True)
        file = path / url_hash[2:]
        timestamp = datetime.datetime.today()
        obj = (timestamp, response)
        with open(file, "xb") as pickle_file:
            pickle.dump(obj, pickle_file)

    def request(self, url: str) -> Response:
        """
        Simple downloader which uses requests get method.
        raises http error

        :param url: An url to any website. The hash of the url is used as key for the cache.
        :return: tuple(response, status)
        """
        get = functools.partial(super(CachedRequest, self).request, url)

        timestamp, response = self._load_cache(url)
        today = datetime.datetime.today()
        valid = datetime.timedelta(days=self._validity)
        if not response or (today - timestamp > valid):
            response = get()
            self._dump_cache(url, response)
        return response


class InstrumentPersistenceMixin:
    """
    Saves/loads the intrument.__dict__ to a shelve database.
    """
    path: str
    isin: str

    def load(self):
        with shelve.open(self.db_instrument) as db:
            self.__dict__.update(db[self.isin])

    def save(self):
        with shelve.open(self.db_instrument) as db:
            _html_element = self.__dict__.pop("_html_element")
            db[self.isin] = self.__dict__
            self.__dict__["_html_element"] = _html_element

    @property
    def db_instrument(self) -> str:
        path = Path(self.path) / "instrument_shelve"
        return path.__str__()


class Instrument(InstrumentPersistenceMixin):
    """
    Represents the instrument.
    """
    name: str
    isin: str
    notation_ids: list[str]
    markets: list[str]
    symbol: str
    _notations: list[Notation]

    def __init__(self, isin: str, request: Request, db_path: str = None,
                 default_exchange="GER", lazy_load=False):

        self._isin = isin
        self._request = request
        self.path = db_path if db_path else ""
        self.default_exchange = default_exchange

        # scrapped attributes:
        self._name = ""
        self._symbol = ""
        self._wkn = ""
        self._type = ""
        self._sector = ""

        self._loaded: bool = False
        self._response: typing.Optional[Response]
        self._last_update: datetime.datetime = datetime.datetime.min
        self._html_element = None
        self._default_notation = None

        try:
            self.load()
            self._loaded = True
        except KeyError:
            if not lazy_load:
                self.update()

    @property
    def isin(self):
        return self._isin

    @property
    def name(self):
        return self._name

    @property
    def symbol(self):
        return self._symbol

    @property
    def wkn(self):
        return self._wkn

    @property
    def type(self):
        return self._type

    @property
    def sector(self):
        return self._sector

    @property
    def notations(self) -> list[Notation]:
        return self._notations

    @property
    def last_update(self):
        return self._last_update

    def update(self) -> None:
        """
        Updates all data from a fresh http response
        :return: None
        """
        self._response = None
        self._parse_notations()
        self._parse_symbol()
        self._parse_name()
        self._parse_wkn()
        self._parse_type()
        self._parse_sector()
        self._last_update = datetime.datetime.now()
        self._default_notation = self.get_notation_by(self.default_exchange)
        self.save()

    def _parse_notations(self):
        self._request_main_page()
        html_element = self.html_element
        markets: list[str] = [str(market).strip() for market in
                              html_element.xpath('//div[@id="exchangesLayer"]/ul/li/a/text()')
                              if market != " "]
        notation_ids: list[str] = list(
            map(lambda x: x.split("=")[1], html_element.xpath('//div[@id="exchangesLayer"]/ul/li/a/@href')))

        with open(FP_MARKETS, "r") as input_json:
            mapping = dict(json.load(input_json))
        exchanges = [mapping.get(market, self.default_exchange) for market in markets]

        self._notations = [Notation(
            idx, market, exchange
        ) for idx, market, exchange in zip(notation_ids, markets, exchanges)]

    def _parse_symbol(self):
        self._symbol = self.html_element.xpath('//div[@class="WERTPAPIER_DETAILS"]/dl[2]/dd[1]/text()')[0]

    def _parse_name(self):
        self._name = self.html_element.xpath('//a[@class="INSTRUMENT"]/@title')[0]

    def _parse_wkn(self):
        self._wkn = self.html_element.xpath('//div[@class="WERTPAPIER_DETAILS"]/dl[1]/dd[1]/input/@value')[0]

    def _parse_type(self):
        type_: str = self.html_element.xpath('//article[@class="CHART_GRAFIK CHART CHART_BREIT"]/script/text()')[0]
        type_ = type_.split("type: ", 1)[1]
        type_ = type_.split(",", 1)[0].replace("'", "")
        self._type = type_

    def _parse_sector(self):
        self._sector = self.html_element.xpath('//div[@class="WERTPAPIER_DETAILS"]/dl[2]/dd[2]/text()')[0]

    def _request_main_page(self):
        if not self._response:
            url = f"https://www.onvista.de/aktien/{self.isin}"
            self._response = self._request.request(url)

    @property
    def html_element(self) -> HtmlElement:
        """
        Represents the response as a lxml html element
        :return: HtmlElement
        """
        if self._html_element is None:
            self._html_element = fromstring(self._response.text)
        return self._html_element

    def get_notation_by(self, exchange: str) -> typing.Optional[Notation]:
        """
        :param exchange: Acronym of market
        :return: Notation or None
        """
        return [notation for notation in self.notations if notation.exchange == exchange][0]

    def get_quotes(self, resolution: typing.Literal["week", "month", "year", "all"], notation: Notation = None) -> list[
        "InstrumentQuote"]:
        """
        Delivers the quotes of the notation i.E market.
        :param resolution: literal["week", "month", "year"]
        :param notation: Notation
        :return: list of instrument quotes
        """
        url = self._get_request_url(resolution, notation if notation else self._default_notation)
        response = self._request.request(url).text
        if not resolution in response:
            raise ValueError(f"Provided {resolution} is not in response {response}.")
        # response of this is a raw_json. It does not comply with a standard json and will not fit directly
        raw_quotes = self._prepare_json(response)
        # [timestamp,"open", "high", "low", "close", "volume"]
        next(iter(raw_quotes))
        timestamp = 0
        quotes = []
        for quote in raw_quotes:
            timestamp += get_timestamp(quote)
            quotes.append(
                InstrumentQuote(
                    resolution, datetime.datetime.fromtimestamp(timestamp),
                    get_open(quote), get_high(quote),
                    get_low(quote), get_close(quote), get_volume(quote)
                )
            )

        return quotes

    @staticmethod
    def _prepare_json(raw_json: str) -> dict:
        """Parses the raw http response to formated recordset"""
        json_ = raw_json.replace("data", '"data"')
        json_ = json_.split("(")[1]
        json_ = json_.replace(")", "")
        json_ = json_.rsplit("\n", maxsplit=5)[0]
        json_ = json_.rstrip(",") + "}"
        return json.loads(json_)["data"]

    @staticmethod
    def _get_request_url(resolution: str, notation: Notation) -> str:
        return f'https://chartdata.onvista.de/minimal/?exchange={notation.exchange}&id={notation.id}' \
               f'&assetType=Stock&quality=realtime&callback=getChart{notation.id}{resolution}' \
               f'&granularity={resolution}' \
               f'&tab={tab_dict[resolution]}'


class InstrumentDatabase:
    """
    Provides interface to instrument shelve database
    """

    def __init__(self, path=""):
        """
        :param path: path to database. Default ""
        """
        self.db_instrument = path + "/instrument_shelve"

    def instruments(self) -> typing.Iterable[Instrument]:
        """
        Iterator through all instrument in data base
        :return: Instrument
        """
        with shelve.open(self.db_instrument) as db:
            for cls_dict in db.values():
                yield self._construct(cls_dict)

    def query(self, **kwargs) -> Instrument:
        """
        Query the data base by keyword

        :key isin: isin string
        :return: Instrument
        """
        with shelve.open(self.db_instrument) as db:
            if "isin" in kwargs:
                cls_dict = db[kwargs.pop("isin")]
                return self._construct(cls_dict)
            else:
                raise KeyError(
                    f"The provided key {next(kwargs)} is not implemented or does not make sense.\n"
                    f"Use 'isin:value' instead."
                )

    @staticmethod
    def _construct(cls_dict) -> Instrument:
        obj = Instrument.__new__(Instrument)
        obj.__dict__.update(cls_dict)
        return obj
