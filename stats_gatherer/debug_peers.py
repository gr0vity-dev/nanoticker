from src.config import Config
from src.get_peers import getPeers
from src.get_api import ApiHandler
from src.webockets import WebsocketHandler
from src.rpc_requests import RpcWrapper
import asyncio


class RepStatApp:
    def __init__(self, config):
        self.config = config
        self.rpc_wrapper = RpcWrapper(config)
        self.api_handler = ApiHandler(self.config, self.rpc_wrapper)
        self.ws_handler = WebsocketHandler(config, self.api_handler)

    async def run_task_forever(self, task_func):
        while True:
            try:
                await task_func()
            except asyncio.CancelledError:
                # If the task is cancelled, exit the loop
                break
            except Exception as e:
                print(f"Exception in {task_func.__name__}: {e}")
                # Optionally, add a delay before restarting the task
                await asyncio.sleep(1)

    def run(self):
        loop = asyncio.get_event_loop()
        tasks = [
            loop.create_task(self.run_task_forever(self.get_peers_task)),
        ]

        try:
            loop.run_until_complete(asyncio.wait(tasks))
        except KeyboardInterrupt:
            print("Interrupted by user, shutting down.")
        finally:
            for task in tasks:
                task.cancel()
            loop.run_until_complete(asyncio.gather(
                *tasks, return_exceptions=True))
            loop.close()

    async def get_peers_task(self):
        await getPeers(self.config, self.rpc_wrapper)

    async def websocket_loop_task(self):
        await self.ws_handler.websocketLoop()

    async def websocket_countdown_task(self):
        await self.ws_handler.websocketCountDown()

    # ... other methods and task implementations


if __name__ == "__main__":
    environment = "LIVE"  # Or BETA, LIVE based on external input
    config = Config(environment)
    app = RepStatApp(config)
    app.run()
