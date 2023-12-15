from src.config import Config
from src.get_peers import getPeers
from src.get_api import ApiHandler
from src.webockets import WebsocketHandler
from src.rpc_requests import RpcWrapper
import asyncio


class RepStatApp:
    def __init__(self, config):
        self.config = config
        self.loop = asyncio.get_event_loop()
        self.rpc_wrapper = RpcWrapper(config)
        self.api_handler = ApiHandler(self.config, self.rpc_wrapper)
        self.ws_handler = WebsocketHandler(config, self.api_handler)
        # Initialize other necessary components

    def run(self):
        # Set up tasks and run the event loop
        try:
            self.loop.run_until_complete(self.setup_tasks())
        except KeyboardInterrupt:
            pass

    async def setup_tasks(self):
        # Create and return asyncio tasks
        futures = [self.get_peers_task(), self.websocket_loop_task(),
                   self.websocket_countdown_task()]
        return await asyncio.wait(futures)

    async def get_peers_task(self):
        await getPeers(self.config, self.rpc_wrapper)

    async def websocket_loop_task(self):
        # Implementation of the websocket loop
        await self.ws_handler.websocketLoop()

    async def websocket_countdown_task(self):
        # Implementation of the websocket loop
        await self.ws_handler.websocketCountDown()

    # ... other methods and task implementations


if __name__ == "__main__":
    environment = "BETA"  # Or BETA, LIVE based on external input
    config = Config(environment)
    app = RepStatApp(config)
    app.run()
