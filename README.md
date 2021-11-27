# pyOnvista
A tiny API for onvista.de financial website.

The API provides at a maximum all available chart data as can be viewed on the webpage.
It does not scrap any recent quotes. So the prupose is to fetch historic quotes as can be viewed on the onvista chart diagrams.

The API core uses package requests to download contents.
The implementation of requests is very flat without deeper exception handling.

It uses the super fast lxml binding to C libxml2 and libxslt instead of beautiful soup
for html parsing. xpath are hardcoded but may be user defined at a later stage.

To get the quotes from the onvista server, the api first scraps some meta data of the instrument.
This will be stored in a shelve database. The database can be access through the provided class
InstrumentDatabase. This avoids traffic and complies with the typical user case. 
Once the metadata is known, the user can fetch the quotes from the server. 
These data is polled every time get_quotes is called.
However, it is possible to use CachedRequest instead of Request classe you poll against 
an http cache stored locally after the first query. 

## Installation:
    pip install pyonvista

## Please note:
The API fakes a request from a chart shown on the instrument page. Therefore, the server sees only a normal 
user behavior like scrolling through the chart data.
However, there may be a misalignment between notification_id and exchange (market). Because not all
acronyms are provided yet or proper. See also markets.json.
The API does not validate the market opening times as provided by onvista and market. It was not recognized why onvista
provides this data with the quote data.

The server may mind the scrapping action when frequencies is high. It is recommended
to use a rotating proxy, or at least rotate user agent and let pass plenty of time.
Please keep also terms of webpage company in mind. This script may harm the terms.

## Usage:
Preliminary you need to know the ISIN of the instrument.
Create an instrument and request quote data by calling .get_quotes

    from pyOnvista import Instrument, Request
    
    # make a configured request. Provide a proper header
    user_agent = "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0"
    header = {'user-agent': user_agent}
    request = Request(header=header)
    
    # make the instrument you wish
    vw = Instrument("DE0007664039", request)
    
    # request quotes
    quotes = vw.get_quotes("month")  # retrieve quotes from default market
    
    # and do some stuff
    for quote in quotes:
        print(quote.timestamp.isoformat(), " high: ", quote.high, " low: ", quote.low)