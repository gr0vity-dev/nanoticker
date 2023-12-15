from src.config import Config
from src.get_api import ApiHandler
from collections import deque
import websockets
import json
from src.helper import timeLog
import time
import asyncio


class WebsocketHandler:
    def __init__(self, config: Config, api_handler: ApiHandler):
        self.config = config
        self.api_handler = api_handler
        self.log = config.log

    async def websocketLoop(self):
        indiPeersPrev = self.config.indiPeersPrev

        try:
            async with websockets.connect(self.config.websocketAddress) as websocket:
                await websocket.send(json.dumps({"action": "subscribe", "topic": "telemetry", "ack": True}))
                ack = json.loads(await websocket.recv())
                if 'ack' in ack:
                    if ack['ack'] == 'subscribe':
                        self.log.info(timeLog("Websocket opened."))
                    else:
                        self.log.warning(
                            timeLog("Could not subscribe to websocket."))
                        return
                else:
                    self.log.warning(
                        timeLog("Could not subscribe to websocket."))
                    return

                while 1:
                    rec = json.loads(await websocket.recv())
                    topic = rec.get("topic", None)
                    if topic:
                        metric = rec["message"]
                        if topic == "telemetry":
                            block_count_tele = -1
                            cemented_count_tele = -1
                            unchecked_count_tele = -1
                            account_count_tele = -1
                            bandwidth_cap_tele = -1
                            peer_count_tele = -1
                            protocol_version_number_tele = -1
                            major_version_tele = -1
                            minor_version_tele = -1
                            patch_version_tele = -1
                            pre_release_version_tele = -1
                            uptime_tele = -1
                            timeStamp_tele = time.time()
                            address_tele = -1
                            port_tele = -1

                            if 'block_count' in metric:
                                block_count_tele = int(metric['block_count'])
                            else:
                                continue  # failed, do next message
                            if 'timestamp' in metric:
                                timeStamp_tele = int(metric['timestamp'])
                            if 'cemented_count' in metric:
                                cemented_count_tele = int(
                                    metric['cemented_count'])
                            if 'unchecked_count' in metric:
                                unchecked_count_tele = int(
                                    metric['unchecked_count'])
                            if 'account_count' in metric:
                                account_count_tele = int(
                                    metric['account_count'])
                            if 'bandwidth_cap' in metric:
                                bandwidth_cap_tele = metric['bandwidth_cap']
                            if 'peer_count' in metric:
                                peer_count_tele = int(metric['peer_count'])
                            if 'protocol_version' in metric:
                                protocol_version_number_tele = int(
                                    metric['protocol_version'])
                            if 'major_version' in metric:
                                major_version_tele = metric['major_version']
                            if 'minor_version' in metric:
                                minor_version_tele = metric['minor_version']
                            if 'patch_version' in metric:
                                patch_version_tele = metric['patch_version']
                            if 'pre_release_version' in metric:
                                pre_release_version_tele = metric['pre_release_version']
                            if 'uptime' in metric:
                                uptime_tele = metric['uptime']
                            if 'address' in metric:
                                address_tele = metric['address']
                            if 'port' in metric:
                                port_tele = metric['port']

                            # calculate individual BPS and CPS
                            BPSPeer = -1
                            CPSPeer = -1
                            previousTimeStamp = deque(
                                [0]*self.config.checkCPSEvery)

                            if timeStamp_tele != -1 and block_count_tele != -1 and cemented_count_tele != -1 and address_tele != -1 and port_tele != -1:
                                found = False
                                for ip in indiPeersPrev:
                                    if ip == address_tele + ':' + port_tele:
                                        found = True
                                        break

                                if not found:
                                    # prepare first history data
                                    self.log.info(
                                        timeLog("Preparing history for: " + address_tele + ':' + port_tele))

                                    timeD = deque(
                                        [0]*self.config.checkCPSEvery)
                                    blockD = deque(
                                        [0]*self.config.checkCPSEvery)
                                    cementD = deque(
                                        [0]*self.config.checkCPSEvery)

                                    timeD.append(timeStamp_tele)
                                    timeD.popleft()
                                    blockD.append(block_count_tele)
                                    blockD.popleft()
                                    cementD.append(cemented_count_tele)
                                    cementD.popleft()
                                    indiPeersPrev[address_tele + ':' + port_tele] = {'timestamp': timeD, 'blockCount': blockD, 'cementCount': cementD,
                                                                                     'unchecked_count': unchecked_count_tele, 'peer_count': peer_count_tele, 'protocol_version': protocol_version_number_tele,
                                                                                     'account_count': account_count_tele, 'bandwidth_cap': bandwidth_cap_tele, 'uptime': uptime_tele,
                                                                                     'major_version': major_version_tele, 'minor_version': minor_version_tele, 'patch_version': patch_version_tele, 'pre_release_version': pre_release_version_tele,
                                                                                     'address': address_tele, 'port': port_tele, 'timestamp_local': time.time()}

                                # peer exist in the history, now we can calculate BPS and CPS
                                else:
                                    previousMax = indiPeersPrev[address_tele +
                                                                ':' + port_tele]['blockCount']
                                    previousCemented = indiPeersPrev[address_tele +
                                                                     ':' + port_tele]['cementCount']
                                    previousTimeStamp = indiPeersPrev[address_tele +
                                                                      ':' + port_tele]['timestamp']

                                    # skip updating if the timestamp has not changed, ie. the telemetry data has not changed
                                    if timeStamp_tele == previousTimeStamp[0]:
                                        continue

                                    if block_count_tele > 0 and previousMax[0] > 0 and (timeStamp_tele - previousTimeStamp[0]) > 0 and previousTimeStamp[0] > 0:
                                        BPSPeer = (
                                            block_count_tele - previousMax[0]) / (timeStamp_tele - previousTimeStamp[0])

                                    if cemented_count_tele > 0 and previousCemented[0] > 0 and (timeStamp_tele - previousTimeStamp[0]) > 0 and previousTimeStamp[0] > 0:
                                        CPSPeer = (
                                            cemented_count_tele - previousCemented[0]) / (timeStamp_tele - previousTimeStamp[0])

                                    timeD = indiPeersPrev[ip]['timestamp']
                                    timeD.append(timeStamp_tele)
                                    timeD.popleft()

                                    blockD = indiPeersPrev[ip]['blockCount']
                                    blockD.append(block_count_tele)
                                    blockD.popleft()

                                    cementD = indiPeersPrev[ip]['cementCount']
                                    cementD.append(cemented_count_tele)
                                    cementD.popleft()

                                    # ms to sec (if reported in ms)
                                    if timeStamp_tele > 9999999999 and previousTimeStamp[0] > 9999999999 and BPSPeer != -1:
                                        BPSPeer = BPSPeer * 1000
                                        CPSPeer = CPSPeer * 1000

                                    indiPeersPrev[ip] = {'timestamp': timeD, 'blockCount': blockD, 'cementCount': cementD,
                                                         'unchecked_count': unchecked_count_tele, 'peer_count': peer_count_tele, 'protocol_version': protocol_version_number_tele,
                                                         'account_count': account_count_tele, 'bandwidth_cap': bandwidth_cap_tele, 'uptime': uptime_tele,
                                                         'major_version': major_version_tele, 'minor_version': minor_version_tele, 'patch_version': patch_version_tele, 'pre_release_version': pre_release_version_tele,
                                                         'address': address_tele, 'port': port_tele, 'bps': BPSPeer, 'cps': CPSPeer, 'timestamp_local': time.time()}

                                    # call the rest of the API calls
                                    self.config.websocketCountDownTimer = time.time()
                                    self.config.apiShouldCall = True
                                    self.config.startTime = time.time()

        except websockets.ConnectionClosed as e:
            self.log.warning(timeLog("Websocket connection to %s was closed" %
                                     self.config.websocketAddress))
            await asyncio.sleep(10)
            self.log.info(timeLog("Reconnecting to %s" %
                          self.config.websocketAddress))
            # try reconnect
            await self.websocketLoop()

        except Exception as e:
            self.log.warning(timeLog(
                "Failed to process websocket telemetry. %r. Websocket reconnection attempt in 60sec" % e))
            await asyncio.sleep(60)
            # try reconnect
            await self.websocketLoop()

    async def websocketCountDown(self):

        while 1:
            if self.config.apiShouldCall and time.time() > self.config.websocketCountDownTimer + self.config.websocketCountDownLimit:
                # if enough time has passed since last run
                if time.time() > self.config.websocketTimer + self.config.runAPIEvery:
                    self.config.websocketTimer = time.time()  # reset timer
                    self.config.websocketCountDownTimer = time.time()  # reset timer
                    self.config.apiShouldCall = False
                    self.config.apiShouldCall = await self.api_handler.getAPI()
            await asyncio.sleep(0.1)
