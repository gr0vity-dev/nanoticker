import aiohttp
import async_timeout
import asyncio
import json
import time
import base64
import re
from src.config import Config


class RpcWrapper:
    def __init__(self, config: Config):
        self.config = config
        self.rpc_timeout = config.rpcTimeout
        self.log = config.log
        self.node_url = config.nodeUrl
        self.node_pw = config.nodePw
        self.node_user = config.nodeUser

    async def fetch(self, url, method='GET', data=None, json_serialize=json.dumps, timeout=None):
        # Basic Authentication setup
        basic_auth = None
        if url == self.node_url and self.node_user and self.node_pw:
            basic_auth = base64.b64encode(
                f"{self.node_user}:{self.node_pw}".encode()).decode()

        try:
            # Creating a new session for each call
            async with aiohttp.ClientSession(json_serialize=json_serialize) as session:
                headers = {
                    'Authorization': f'Basic {basic_auth}'} if basic_auth else {}

                with async_timeout.timeout(timeout or self.rpc_timeout):
                    if method == 'GET':
                        response = await session.get(url, headers=headers)
                    else:  # Assuming POST
                        response = await session.post(url, json=data, headers=headers)

                    # Check response and return accordingly
                    if response.status == 200:
                        result = await response.json() if method == 'POST' else await response.text()
                        return result
                    else:
                        self.log.warning(
                            f"{method} request failed with status {response.status} for URL: {url}")

        except asyncio.TimeoutError:
            self.log.warning(f"Request timed out for URL: {url}")
        except Exception as e:
            self.log.error(
                f"Exception occurred in fetch method for URL {url}: {e}")
        return None

    async def request_get(self, url, timeout=None):
        response_text = await self.fetch(url, method='GET', timeout=timeout or self.rpc_timeout)
        if response_text:
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # Handle JSON decoding error
                pass
        return None

    async def request_post(self, url, data, timeout=None):
        response_json = await self.fetch(url, method='POST', data=data, timeout=timeout or self.rpc_timeout)
        return response_json

    async def get_available_supply(self):
        params = {"action": "available_supply"}
        call_time = time.time()

        # Use the fetch method with POST
        response_json = await self.fetch(self.node_url, method='POST', data=params)

        if response_json is not None:
            time_diff = round((time.time() - call_time) * 1000)
            try:
                # Extract the 'available' field from the JSON response
                available_supply = response_json["available"]
                return [available_supply, True, time_diff, response_json]
            except KeyError:
                self.log.error("Key 'available' not found in response JSON.")
                return [None, False, time_diff, response_json]
        else:
            self.log.warning("Bad response from node.")
            return [None, False, 0, None]

    async def get_monitor(self, url):
        response_text = await self.fetch(url)
        if response_text:
            try:
                response_json = json.loads(response_text)
                if int(response_json.get('currentBlock', 0)) > 0:
                    return [response_json, True, url, time.time(), response_text]
            except json.JSONDecodeError as e:
                self.log.error(
                    f"JSON decoding failed for response: {response_text}")
            return [{}, False, url, time.time(), response_text]
        else:
            self.log.warning(f"Failed to fetch monitor data from {url}")
            return [{}, False, url, time.time(), None]

    async def verify_monitor(self, url):
        # Clean the URL by removing unwanted extensions
        cleaned_url = re.sub(r'\.htm(l)?$', '', url)

        # Append "/api.php" if it's not already there
        query_url = cleaned_url
        if not cleaned_url.endswith('/api.php'):
            query_url = cleaned_url + '/api.php'

        response_text = await self.fetch(query_url)
        if response_text:
            try:
                response_json = json.loads(response_text)
                if int(response_json.get('currentBlock', 0)) > 0:
                    return [response_json['nanoNodeAccount'], cleaned_url]
            except json.JSONDecodeError:
                self.log.error(
                    f"JSON decoding failed for response: {response_text}")
            except KeyError:
                self.log.error(f"Key error in response JSON: {response_json}")
        else:
            self.log.warning(
                f"Failed to fetch data for monitor verification from {url}")
        return None

    async def get_telemetry_rpc(self, params, ipv6):
        call_time = time.time()
        response_json = await self.fetch(self.node_url, method='POST', data=params)
        if response_json is not None:
            time_diff = round((time.time() - call_time) * 1000)  # Request time
            return [response_json, True, params['address'], ipv6, time_diff, time.time(), response_json]
        else:
            self.log.warning(
                "Bad telemetry response from node. Probably timeout.")
            return [{}, False, params['address'], ipv6, 0, time.time(), None]

    async def get_regular_rpc(self, params):
        call_time = time.time()
        response_json = await self.fetch(self.node_url, method='POST', data=params)
        if response_json is not None:
            time_diff = round((time.time() - call_time) * 1000)
            return [response_json, True, time_diff, response_json]
        else:
            self.log.warning("Bad RPC response from node.")
            return [{}, False, 0, None]
