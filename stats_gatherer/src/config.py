from src.known_reps import get_reps, get_blacklist
from collections import deque  # for array shifting
import time
import logging
from pathlib import Path


class Config:
    def __init__(self, env):
        self.env = env
        self.setup_environment()

    def setup_environment(self):
        if self.env.lower() in ("dev", "develop", "local"):
            # Set up DEV environment variables
            self.nodeUrl = 'https://rpcproxy.bnano.info/proxy'

            # ... other DEV config
        elif self.env.lower() in ("beta"):
            self.nodeUrl = 'https://rpcproxy.bnano.info/proxy'  # beta
            self.telemetryAddress = 'nanobeta'
            self.telemetryPort = '54000'
            self.websocketAddress = 'wss://nanolooker.bnano.info/ws'
            self.logFile = "repstat.log"
            # self.statFile = '/var/www/localhost/htdocs/json/stats.json'  # netdata container
            # self.monitorFile = '/var/www/localhost/htdocs/json/monitors.json'  # netdata container
            self.statFile = 'stats.json'  # netdata container
            self.monitorFile = 'monitors.json'  # netdata container
            self.activeCurrency = 'nano-beta'  # nano, banano or nano-beta
            # ninjaMonitors = 'https://beta.mynano.ninja/api/accounts/monitors' #beta
            self.ninjaMonitors = ''
            self.aliasUrl = ''
            # telemetry is retrived with another command for this account
            self.localTelemetryAccount = 'nano_18cgy87ikc4ruyh5aqwqe6dybe9os1ip3681y9wukypz5j7kgh35uxftss1x'
            # telemetry data from nodes not reported withing this interval (seconds) will be dropped from the list (until they report again)
            self.websocketPeerDropLimit = 60
            self.additional_monitors = False
        elif self.env.lower() in ("main", "live", "prod"):
            # Set up LIVE environment variables
            self.nodeUrl = 'http://[::1]:7076'
            self.additional_monitors = True
            # ... other LIVE config
        else:
            raise ValueError(f"{self.env} is not a valid Environment")

        # Common configurations for all environments
        self.common_config()

    def common_config(self):
        # Set up common configurations
        checkCPSEvery = 1
        self.checkCPSEvery = checkCPSEvery
        self.repsInit = get_reps(self.env)
        self.blacklist = get_blacklist(self.env)
        self.logFile = "repstat.log"
        self.minCount = 1
        # Speed test source account
        self.workUrl = 'http://127.0.0.1:9971'
        self.workDiff = 'fffffff800000000'  # 1x
        self.source_account = ''
        self.priv_key = ''
        self.speedtest_rep = ''
        self.speedtest_websocket_1 = ''  # Preferably in another country
        self.speedtest_websocket_2 = ''  # Leave blank if you don't have one
        # ping/2 ms latency for the websocket node to be deducted from the speed delay
        self.speedtest_websocket_ping_offset_1 = 45
        # ping/2 ms latency for the websocket node to be deducted from the speed delay
        self.speedtest_websocket_ping_offset_2 = 20

        """LESS CUSTOM VARS"""
        self.minCount = 1  # initial required block count
        self.monitorTimeout = 3  # http request timeout for monitor API
        self.rpcTimeout = 3  # node rpc timeout

        # run API check (at fastest) every X sec (the websocket on beta runs every 18sec and main every 60)
        self.runAPIEvery = 10
        self.runPeersEvery = 120  # run peer check every X sec
        self.runStatEvery = 3600  # publish stats to blockchain every x sec
        self.maxURLRequests = 250  # maximum concurrent requests
        # call API if x sec has passed since last websocket message
        self.websocketCountDownLimit = 1
        self.runSpeedTestEvery = 120  # run speed test every X sec

        """CONSTANTS"""
        self.pLatestVersionStat = 0  # percentage running latest protocol version
        self.pTypesStat = 0  # percentage running tcp
        self.pStakeTotalStat = 0  # percentage connected online weight of maximum
        # percentage of connected online weight of maxium required for voting
        self.pStakeRequiredStat = 0
        # percentage of connected online weight that is on latest version
        self.pStakeLatestVersionStat = 0
        self.confCountLimit = 100  # lower limit for block count to include confirmation average
        self.confSpanLimit = 10000  # lower limit for time span to include confirmation average

        """VARIABLES"""
        self.reps = self.repsInit
        self.latestOnlineWeight = 0  # used for calculating PR status
        self.latestRunStatTime = 0  # fine tuning loop time for stats
        self.latestGlobalBlocks = []
        self.latestGlobalPeers = []
        self.latestGlobalDifficulty = []

        # For BPS/CPS calculations (array with previous values to get a rolling window)
        self.previousMaxBlockCount = deque([0]*checkCPSEvery)
        self.previousMaxConfirmed = deque([0]*checkCPSEvery)
        self.previousMedianBlockCount = deque([0]*checkCPSEvery)
        self.previousMedianConfirmed = deque([0]*checkCPSEvery)
        self.previousMedianTimeStamp = deque([0]*checkCPSEvery)
        self.previousMaxBlockCount_pr = deque([0]*checkCPSEvery)
        self.previousMaxConfirmed_pr = deque([0]*checkCPSEvery)
        self.previousMedianBlockCount_pr = deque([0]*checkCPSEvery)
        self.previousMedianConfirmed_pr = deque([0]*checkCPSEvery)
        self.previousMedianTimeStamp_pr = deque([0]*checkCPSEvery)

        self.previousLocalTimeStamp = deque([0]*checkCPSEvery)
        self.previousLocalMax = deque([0]*checkCPSEvery)
        self.previousLocalCemented = deque([0]*checkCPSEvery)

        # individual BPS CPS object
        self.indiPeersPrev = {'ip': {}}

        # IPs that has a monitor. To get rid of duplicates in telemetry
        self.monitorIPExistArray = {'ip': {}}

        # account / alias pairs
        self.aliases = []

        # Websocket control timer for when to call monitor API
        self.websocketTimer = time.time()
        self.websocketCountDownTimer = time.time()
        self.startTime = time.time()
        self.apiShouldCall = True

        # speed test memory
        self.speedtest_latest = []
        self.speedtest_latest_ms = [0]
        self.speedtest_last_valid = time.time()

        filename = Path(self.logFile)
        filename.touch(exist_ok=True)
        logging.basicConfig(level=logging.INFO, filename=self.logFile,
                            filemode='a+', format='%(name)s - %(levelname)s - %(message)s')
        self.log = logging.getLogger(__name__)
