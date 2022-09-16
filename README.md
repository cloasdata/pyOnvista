# pyonvista
A tiny python wrapper to the non-public onvista.de REST-Api.

As the API is not public user shall assume that the usage of this package harms the
website user agreements. However, this version now avoids any web scrapping for metadata.

You can search for an instrument and get its quote data. 
The quote data can be limit by resolution and date.

The wrapper now also works with instruments other than stocks. Also for example data from ETF
can be requested. 

Im not planing to add other API Endpoints at the moment as long as nobody gives me a good reason for this.

Additionally the wrapper now is asynchronous. User should be aware of asyncio or async programming.


## Installation
    pip install pyonvista

## Usage
```python
import asyncio
import aiohttp
import pprint

from pyonvista import PyOnVista

async def main():
    client = aiohttp.ClientSession()
    api = PyOnVista()
    await api.install_client(client)
    async with client:
        instruments = await api.search_instrument("VW")
        instrument = await api.request_instrument(instruments[0])
        quotes = await api.request_quotes(instrument, )
        pprint.pprint(instrument)
        pprint.pprint(quotes[:3])
        # prints a lot of information of VW Stonk
        # try a etf
        instruments = await api.search_instrument(key="IE00B42NKQ00")
        quotes = await api.request_quotes(instruments[0])
    pprint.pprint(quotes[0].instrument)

    await client.close()
    await asyncio.sleep(.1)

if __name__ == '__main__':
    asyncio.run(main())
```