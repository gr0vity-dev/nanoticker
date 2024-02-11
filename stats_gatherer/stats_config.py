from dotenv import load_dotenv
import os

load_dotenv()  # This loads the environment variables from .env

env = os.getenv('ENV')
node_rpc_url = os.getenv('NODE_RPC_URL')
node_rpc_user = os.getenv('NODE_RPC_USER')
node_rpc_pw = os.getenv('NODE_RPC_PW')
node_ws_url = os.getenv('NODE_WS_URL')
node_account = os.getenv('NODE_ACCOUNT')  # special treatment during telemetry

# default values if not set
if not node_rpc_url or not node_ws_url:
    if env.lower() in ("dev", "develop", "local"):
        # Default values for DEV environment
        node_rpc_url = node_rpc_url or 'http://127.0.0.1:45000'
        node_ws_url = node_ws_url or 'http://127.0.0.1:47000'
    elif env.lower() == "beta":
        # Default values for BETA environment
        node_rpc_url = node_rpc_url or 'http://127.0.0.1:55000'
        node_ws_url = node_ws_url or 'http://127.0.0.1:57000'
    elif env.lower() in ("main", "live", "prod"):
        # Default values for BETA environment
        # 'https://nanowallet.cc/proxy'  # 'http://127.0.0.1:7076'
        node_rpc_url = node_rpc_url or 'http://127.0.0.1:7076'
        # 'wss://nanowallet.cc/ws'  # 'http://127.0.0.1:7078'
        node_ws_url = node_ws_url or 'http://127.0.0.1:7078'
