from src.config import Config
import asyncio
import aiohttp
from src.config import Config
from src.rpc_requests import RpcWrapper


async def test_urls(urls):
    for rep in urls:
        print(await rpc.verify_monitor(rep))

config = Config("Live")
rpc = RpcWrapper(config)
reps = config.reps


# Run the asynchronous URL testing
results = asyncio.run(test_urls(reps))
# print(results)
