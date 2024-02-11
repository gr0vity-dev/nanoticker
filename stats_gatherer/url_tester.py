from src.config import Config
import asyncio
import aiohttp
from src.config import Config


async def is_reachable(session, url):
    try:
        async with session.get(url, timeout=0.5) as response:
            return response.status == 200
    except:
        return False


async def has_api_endpoint(session, url):
    try:
        async with session.get(url + '/api.php', timeout=2) as response:
            return response.status == 200
    except:
        return False


async def test_url(session, url):
    reachable = await is_reachable(session, url)
    api = await has_api_endpoint(session, url) if reachable else False
    return {'url': url, 'reachable': reachable, 'api': api}


async def test_urls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [test_url(session, url) for url in urls]
        results = await asyncio.gather(*tasks)
        # return sorted(results, key=lambda x: (x['api'], x['reachable']), reverse=True)
        return [result['url'] for result in results if result['api']]

config = Config("Live")
reps = config.reps

# Run the asynchronous URL testing
results = asyncio.run(test_urls(reps))
print(results)
