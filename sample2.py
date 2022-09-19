"""
This script demonstrate performance.
"""
import asyncio
import time

import aiohttp
import pyonvista


async def main():
    loop = asyncio.get_event_loop()
    client = aiohttp.ClientSession()
    api = pyonvista.PyOnVista()
    await api.install_client(client)
    async with client:
        # get Instruments form top/flop endpoint:
        response = await client.get(url="https://api.onvista.de/api/v2/indices/20735/top_flop?perPage=50")
        raw_data = await response.json()
        # make instruments
        instruments_data = raw_data["topList"] + raw_data["flopList"]
        instruments = [pyonvista.Instrument.from_json(data["instrument"]) for data in instruments_data]
        print(f"Got {len(instruments)} instruments")

        # make coro and wait for them
        async def work(instrument) -> int:
            await api.request_instrument(instrument)
            return len(await api.request_quotes(instrument))

        pending = set(loop.create_task(work(instrument)) for instrument in instruments)
        time_taken = time.time()
        total_quotes = 0
        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_EXCEPTION)
            for t in done:
                total_quotes += t.result()

        time_taken = time.time() - time_taken
        print(f"Crawled {len(done)} instruments in {time_taken:.2f} seconds.\n"
              f"Average is {time_taken / len(done):.2f} instruments per second.\n"
              f"Total quotes {total_quotes}.")

        # prints
        # Crawled 20 instruments in 0.34 seconds.
        # Average is 0.02 instruments per second.
        # Total quotes 3503.
    await client.close()
    await asyncio.sleep(0.1)


if __name__ == '__main__':
    asyncio.run(main())
