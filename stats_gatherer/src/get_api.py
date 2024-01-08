from src.config import Config
from src.rpc_requests import RpcWrapper
from src.helper import time_log, median, chunks, percentile, medianNormal
import datetime
import time
import asyncio
import async_timeout
import re
import json


class ApiHandler:
    def __init__(self, config: Config, rpc_wrapper: RpcWrapper):
        self.config = config
        self.rpc_wrapper = rpc_wrapper
        self.log = config.log

    async def getAPI(self):
        PRStatusLocal = False
        telemetryPeers = []

        # GET TELEMETRY FOR LOCAL ACCOUNT (can't use normal telemetry)
        try:
            apistartTime = time.time()

            # get block count
            params = {
                "action": "telemetry",
                "address": self.config.telemetryAddress,
                "port": self.config.telemetryPort
            }
            resp = await self.rpc_wrapper.get_regular_rpc(params)
            telemetry = resp[0]

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
            weight = -1
            PRStatus = False

            # calculate max/min/medians using telemetry data. Init first
            countData = []
            cementedData = []
            uncheckedData = []
            peersData = []
            peerHasEnoughBlocks = False

            if 'block_count' in telemetry:
                block_count_tele = int(telemetry['block_count'])
                if block_count_tele >= self.config.minCount:  # only add to stats if above limit
                    peerHasEnoughBlocks = True
                    countData.append(block_count_tele)
            if peerHasEnoughBlocks:
                if 'timestamp' in telemetry:
                    timeStamp_tele = int(telemetry['timestamp'])
                if 'cemented_count' in telemetry:
                    cemented_count_tele = int(telemetry['cemented_count'])
                    cementedData.append(cemented_count_tele)
                if 'unchecked_count' in telemetry:
                    unchecked_count_tele = int(telemetry['unchecked_count'])
                    uncheckedData.append(unchecked_count_tele)
                if 'account_count' in telemetry:
                    account_count_tele = int(telemetry['account_count'])
                if 'bandwidth_cap' in telemetry:
                    bandwidth_cap_tele = telemetry['bandwidth_cap']
                if 'peer_count' in telemetry:
                    peer_count_tele = int(telemetry['peer_count'])
                    peersData.append(peer_count_tele)
                if 'protocol_version' in telemetry:
                    protocol_version_number_tele = int(
                        telemetry['protocol_version'])
                if 'major_version' in telemetry:
                    major_version_tele = telemetry['major_version']
                if 'minor_version' in telemetry:
                    minor_version_tele = telemetry['minor_version']
                if 'patch_version' in telemetry:
                    patch_version_tele = telemetry['patch_version']
                if 'pre_release_version' in telemetry:
                    pre_release_version_tele = telemetry['pre_release_version']
                if 'uptime' in telemetry:
                    uptime_tele = telemetry['uptime']

                BPSLocal = -1
                if block_count_tele > 0 and self.config.previousLocalMax[0] > 0 and (timeStamp_tele - self.config.previousLocalTimeStamp[0]) > 0 and self.config.previousLocalTimeStamp[0] > 0:
                    BPSLocal = (
                        block_count_tele - self.config.previousLocalMax[0]) / (timeStamp_tele - self.config.previousLocalTimeStamp[0])
                CPSLocal = -1
                if cemented_count_tele > 0 and self.config.previousLocalCemented[0] > 0 and (timeStamp_tele - self.config.previousLocalTimeStamp[0]) > 0 and self.config.previousLocalTimeStamp[0] > 0:
                    CPSLocal = (cemented_count_tele - self.config.previousLocalCemented[0]) / (
                        timeStamp_tele - self.config.previousLocalTimeStamp[0])

                # ms to sec (if reported in ms)
                if timeStamp_tele > 9999999999 and self.config.previousLocalTimeStamp[0] > 9999999999 and BPSLocal != -1:
                    BPSLocal = BPSLocal * 1000
                    CPSLocal = CPSLocal * 1000

                if timeStamp_tele > 0:
                    self.config.previousLocalTimeStamp.append(timeStamp_tele)
                    self.config.previousLocalTimeStamp.popleft()
                if block_count_tele > 0:
                    self.config.previousLocalMax.append(block_count_tele)
                    self.config.previousLocalMax.popleft()
                if cemented_count_tele > 0:
                    self.config.previousLocalCemented.append(
                        cemented_count_tele)
                    self.config.previousLocalCemented.popleft()

                # get weight
                params = {
                    "action": "account_weight",
                    "account": self.config.localTelemetryAccount
                }
                reqTime = '0'
                try:
                    resp_weight = await self.rpc_wrapper.get_regular_rpc(params)
                    reqTime = resp_weight[2]
                    if 'weight' in resp_weight[0]:
                        weight = int(resp_weight[0]['weight']) / \
                            int(1000000000000000000000000000000)
                        if (weight >= self.config.latestOnlineWeight*0.001):
                            PRStatus = True
                            PRStatusLocal = True  # used for comparing local BPS/CPS with the rest
                        else:
                            PRStatus = False
                except Exception as e:
                    self.log.warning(
                        time_log("Could not read local weight from node RPC. %r" % e))
                    pass

                teleTemp = {"ip": '', "protocol_version": protocol_version_number_tele, "type": "", "weight": weight, "account": self.config.localTelemetryAccount,
                            "block_count": block_count_tele, "cemented_count": cemented_count_tele, "unchecked_count": unchecked_count_tele,
                            "account_count": account_count_tele, "bandwidth_cap": bandwidth_cap_tele, "peer_count": peer_count_tele, "bps": BPSLocal, "cps": CPSLocal,
                            "vendor_version": str(major_version_tele) + '.' + str(minor_version_tele) + '.' + str(patch_version_tele) + '.' + str(pre_release_version_tele), "uptime": uptime_tele, "PR": PRStatus, "req_time": reqTime, "time_stamp": timeStamp_tele,
                            "tsu": 0}

                telemetryPeers.append(teleTemp)  # add local account rep

        except Exception as e:
            self.log.warning(
                time_log("Could not read local telemetry from node RPC. %r" % e))
            pass

        # GET TELEMETRY DATA FROM PEERS

        # PR ONLY
        countData_pr = []
        cementedData_pr = []
        uncheckedData_pr = []
        peersData_pr = []

        try:
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
            address_tele = ''
            port_tele = ''
            BPSPeer = -1
            CPSPeer = -1
            tsuDiff = 0

            # Use the latest updated data from telemetry websocket
            indiPeersPrevCopy = dict(self.config.indiPeersPrev)
            for key in indiPeersPrevCopy:
                peerHasEnoughBlocks = False
                if key == 'ip':
                    continue
                metric = indiPeersPrevCopy[key]

                # drop peer from the list if too old
                if 'timestamp_local' in metric:
                    timestamp_local_tele = metric['timestamp_local'] + \
                        self.config.websocketCountDownLimit + \
                        (time.time() - apistartTime)
                    tsuDiff = time.time() - timestamp_local_tele
                    if time.time() > timestamp_local_tele + self.config.websocketPeerDropLimit:
                        del self.config.indiPeersPrev[key]
                        self.log.info(
                            time_log("Dropping peer telemetry data due to inactivity: " + key))
                        continue

                if 'blockCount' in metric:
                    block_count_tele = int(metric['blockCount'][-1])
                    if block_count_tele >= self.config.minCount:  # only add to stats if above limit
                        peerHasEnoughBlocks = True
                        countData.append(block_count_tele)

                if peerHasEnoughBlocks:
                    if 'timestamp' in metric:
                        timeStamp_tele = int(metric['timestamp'][-1])

                    if 'cementCount' in metric:
                        cemented_count_tele = int(metric['cementCount'][-1])
                        cementedData.append(cemented_count_tele)

                    if 'unchecked_count' in metric:
                        unchecked_count_tele = int(metric['unchecked_count'])
                        uncheckedData.append(unchecked_count_tele)

                    if 'account_count' in metric:
                        account_count_tele = int(metric['account_count'])
                    if 'bandwidth_cap' in metric:
                        bandwidth_cap_tele = metric['bandwidth_cap']
                    if 'peer_count' in metric:
                        peer_count_tele = int(metric['peer_count'])
                        peersData.append(peer_count_tele)
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
                    if 'bps' in metric:
                        BPSPeer = metric['bps']
                    if 'cps' in metric:
                        CPSPeer = metric['cps']

                    teleTemp = {"ip": '['+address_tele+']:'+port_tele,
                                "protocol_version": protocol_version_number_tele,
                                "type": "",
                                "weight": -1,
                                "account": "",
                                "block_count": block_count_tele,
                                "cemented_count": cemented_count_tele,
                                "unchecked_count": unchecked_count_tele,
                                "account_count": account_count_tele,
                                "bandwidth_cap": bandwidth_cap_tele,
                                "peer_count": peer_count_tele,
                                "bps": BPSPeer,
                                "cps": CPSPeer,
                                "vendor_version": str(major_version_tele) + '.' + str(minor_version_tele) + '.' + str(patch_version_tele) + '.' + str(pre_release_version_tele),
                                "uptime": uptime_tele,
                                "PR": False,
                                "req_time": '0',
                                "time_stamp": timeStamp_tele,
                                "tsu": tsuDiff}

                    telemetryPeers.append(teleTemp)

        except Exception as e:
            self.log.warning(
                time_log("Could not read raw telemetry from node RPC. %r" % e))
            pass

        # GET WEIGHT FROM CONFIRMATION QUORUM
        params = {
            "action": "confirmation_quorum",
            "peer_details": True,
        }
        try:
            resp = await self.rpc_wrapper.get_regular_rpc(params)

            # Find matching IP and include weight in original peer list
            if 'peers' in resp[0]:
                for peer in resp[0]['peers']:
                    for i, cPeer in enumerate(telemetryPeers):
                        if peer['ip'] == cPeer['ip'] and peer['ip'] != '':
                            # append the relevant PR stats here as well
                            weight = peer['weight']
                            if weight != -1:  # only update if it has been given
                                weight = int(weight) / \
                                    int(1000000000000000000000000000000)
                                if (weight >= self.config.latestOnlineWeight*0.001):
                                    PRStatus = True
                                    if cPeer['block_count'] != -1:
                                        countData_pr.append(
                                            int(cPeer['block_count']))
                                    if cPeer['cemented_count'] != -1:
                                        cementedData_pr.append(
                                            int(cPeer['cemented_count']))
                                    if cPeer['unchecked_count'] != -1:
                                        uncheckedData_pr.append(
                                            int(cPeer['unchecked_count']))
                                    if cPeer['peer_count'] != -1:
                                        peersData_pr.append(
                                            int(cPeer['peer_count']))
                                else:
                                    PRStatus = False

                            # update previous vaule
                            telemetryPeers[i] = dict(
                                cPeer, **{"weight": weight, "account": peer['account'], "PR": PRStatus})
                            continue

        except Exception as e:
            self.log.warning(
                time_log("Could not read quorum from node RPC. %r" % e))
            pass

        # Append the BPS CPS data
        bpsData = []
        cpsData = []
        bpsData_pr = []
        cpsData_pr = []

        # Append bandwidth data
        bwData = []
        bwData_pr = []

        try:
            # Also include block_count to determine correct max values later
            for p in telemetryPeers:
                if p['bps'] != -1 and p['block_count'] != -1:
                    # skip if the node is out of sync
                    if int(p['block_count']) < self.config.minCount:
                        continue

                    list = [float(p['bps']), int(p['block_count'])]
                    bpsData.append(list)
                    if (p['PR'] == True):
                        bpsData_pr.append(list)

                if p['cps'] != -1 and p['cemented_count'] != -1:
                    list = [float(p['cps']), int(p['cemented_count'])]
                    cpsData.append(list)
                    if (p['PR'] == True):
                        cpsData_pr.append(list)

                if p['bandwidth_cap'] != -1:
                    bw = int(p['bandwidth_cap'])
                    bwData.append(bw)
                    if (p['PR'] == True):
                        bwData_pr.append(bw)

        except Exception as e:
            self.log.warning(
                time_log("Could not append BPS and CPS data. %r" % e))
            pass

        # GET MONITOR DATA
        # self.log.info(time_log("Get API"))
        jsonData = []
        """Split URLS in max X concurrent requests"""
        for chunk in chunks(self.config.reps, self.config.maxURLRequests):
            tasks = []
            for path in chunk:
                if len(path) > 6:
                    if path[-4:] != '.htm':
                        tasks.append(asyncio.ensure_future(
                            self.rpc_wrapper.get_monitor('%s/api.php' % path)))
                    else:
                        tasks.append(asyncio.ensure_future(
                            self.rpc_wrapper.get_monitor(path)))

            try:
                with async_timeout.timeout(self.config.monitorTimeout):
                    await asyncio.gather(*tasks)

            except asyncio.TimeoutError as t:
                # self.log.warning(time_log('Monitor API read timeout: %r' %t))
                pass
            except Exception as e:
                self.log.warning(time_log(e))

            for i, task in enumerate(tasks):
                try:
                    if task.result() is not None and task.result():
                        if (task.result()[1]):
                            jsonData.append(
                                [task.result()[0], task.result()[3]])
                            # self.log.info(time_log('Valid: ' + task.result()[0]['nanoNodeName']))
                        else:
                            self.log.warning(time_log('Could not read json from %s. Result: %s' % (
                                task.result()[2], task.result()[4])))

                except Exception as e:
                    # for example when tasks timeout
                    self.log.warning(
                        time_log('Could not read response. Error: %r' % e))
                    pass

                finally:
                    if task.done() and not task.cancelled():
                        task.exception()  # this doesn't raise anything, just mark exception retrieved

        syncData = []
        conf50Data = []
        conf75Data = []
        conf90Data = []
        conf99Data = []
        confAveData = []
        memoryData = []
        procTimeData = []
        multiplierData = []
        monitorCount = 0

        # PR ONLY
        syncData_pr = []
        conf50Data_pr = []
        conf75Data_pr = []
        conf90Data_pr = []
        conf99Data_pr = []
        confAveData_pr = []
        memoryData_pr = []
        procTimeData_pr = []
        multiplierData_pr = []
        monitorCount_pr = 0

        tsu = -1  # time since update not valid for node monitors

        # Convert all API json inputs
        fail = False  # If a REP does not support one or more of the entries
        supportedReps = []  # reps supporting all parameters
        telemetryReps = []  # reps collected with telemetry

        try:
            if jsonData is None or type(jsonData[0][0]) == bool:
                # self.log.info(time_log('type error'))
                return

        except:
            return

        for js in jsonData:
            j = js[0]
            if len(j) > 0:
                isTelemetryMatch = False
                monitorCount += 1
                try:
                    count = int(j['currentBlock'])

                    # skip if the node is out of sync
                    if count < self.config.minCount:
                        continue
                except Exception as e:
                    count = 0
                    continue

                try:
                    name = j['nanoNodeName']
                except Exception as e:
                    name = -1
                    fail = True

                # Validate if the monitor is for nano, banano or nano-beta (if possible)
                try:
                    currency = j['currency']
                    if currency != self.config.activeCurrency:
                        self.log.info(
                            time_log('Bad currency setting: ' + name))
                        continue
                except Exception as e:
                    pass

                try:
                    nanoNodeAccount = j['nanoNodeAccount']
                except Exception as e:
                    nanoNodeAccount = -1
                    fail = True

                try:
                    protocolVersion = j['protocol_version']
                except Exception as e:
                    protocolVersion = -1
                    pass

                try:
                    version = j['version']
                except Exception as e:
                    version = -1
                    pass

                try:
                    storeVendor = j['store_vendor']
                except Exception as e:
                    storeVendor = -1
                    pass

                try:
                    weight = int(j['votingWeight'])
                    if (weight >= self.config.latestOnlineWeight*0.001):
                        PRStatus = True
                    else:
                        PRStatus = False
                except Exception as e:
                    weight = -1
                    PRStatus = False
                    pass

                try:
                    cemented = int(j['cementedBlocks'])
                except Exception as e:
                    cemented = -1
                    fail = True
                try:
                    unchecked = int(j['uncheckedBlocks'])
                except Exception as e:
                    unchecked = -1
                    fail = True
                try:
                    peers = int(j['numPeers'])
                except Exception as e:
                    peers = -1
                    fail = True
                try:
                    sync = float(j['blockSync'])
                except Exception as e:
                    sync = -1
                    fail = True
                try:
                    conf50 = int(j['confirmationInfo']['percentile50'])
                except Exception as e:
                    conf50 = -1
                    fail = True
                try:
                    conf75 = int(j['confirmationInfo']['percentile75'])
                except Exception as e:
                    conf75 = -1
                    fail = True
                try:
                    conf90 = int(j['confirmationInfo']['percentile90'])
                except Exception as e:
                    conf90 = -1
                    fail = True
                try:
                    conf99 = int(j['confirmationInfo']['percentile99'])
                except Exception as e:
                    conf99 = -1
                    fail = True
                try:
                    confAve = int(j['confirmationInfo']['average'])
                except Exception as e:
                    confAve = -1
                    fail = True
                try:
                    confCount = int(j['confirmationInfo']['count'])
                except Exception as e:
                    confCount = -1
                try:
                    confSpan = int(j['confirmationInfo']['timeSpan'])
                except Exception as e:
                    confSpan = -1
                try:
                    memory = int(j['usedMem'])
                except Exception as e:
                    memory = -1
                    fail = True
                try:
                    procTime = int(j['apiProcTime'])
                except Exception as e:
                    procTime = -1
                    fail = True
                try:
                    multiplier = float(j['active_difficulty']['multiplier'])
                except Exception as e:
                    multiplier = -1
                    fail = True

                bps = -1
                cps = -1
                bw = -1

                try:
                    # Match IP and replace weight and telemetry data
                    skipPeer = False
                    for p in telemetryPeers:
                        # first check if the account exist in the self.config.monitorIPExistArray (monitors whose URL was guessed from IP)
                        tempIP = p['ip']
                        ipFound = False
                        if tempIP != "":
                            if '[::ffff:' in tempIP:  # ipv4
                                tempIP = re.search(
                                    'ffff:(.*)\]:', tempIP).group(1)

                            for ip in self.config.monitorIPExistArray:
                                # include this
                                if tempIP == ip and self.config.monitorIPExistArray[ip]['account'] == str(nanoNodeAccount):
                                    ipFound = True
                                    break

                        if str(nanoNodeAccount) == str(p['account']) or ipFound:
                            if int(p['weight']) != -1:  # only update if it has been given
                                weight = int(p['weight'])

                            # telemetry
                            if p['vendor_version'] != -1:
                                version = p['vendor_version']
                            if p['protocol_version'] != -1:
                                protocolVersion = int(p['protocol_version'])
                            if p['block_count'] != -1:
                                # skip if the node is out of sync
                                if int(p['block_count']) < self.config.minCount:
                                    skipPeer = True

                                isTelemetryMatch = True  # only show as telemetry if there are actual data available
                                count = int(p['block_count'])
                            if p['cemented_count'] != -1:
                                cemented = int(p['cemented_count'])
                            if p['unchecked_count'] != -1:
                                unchecked = int(p['unchecked_count'])
                            if p['peer_count'] != -1:
                                peers = int(p['peer_count'])
                            if int(p['req_time']) >= 0:
                                procTime = int(p['req_time'])
                            if p['bps'] != -1:
                                bps = float(p['bps'])
                            if p['cps'] != -1:
                                cps = float(p['cps'])
                            if p['tsu'] != -1:
                                tsu = float(p['tsu'])
                            if p['bandwidth_cap'] != -1:
                                bw = int(p['bandwidth_cap'])
                            if p['PR'] == True:
                                PRStatus = True
                                monitorCount_pr += 1
                            else:
                                PRStatus = False
                            break

                except Exception as e:
                    self.log.warning(
                        time_log("Could not match ip and replace weight and telemetry data. %r" % e))
                    pass

                # skip if the node is out of sync
                try:
                    if skipPeer == True:
                        continue

                    if (sync > 0):
                        syncData.append(sync)
                        if (PRStatus):
                            syncData_pr.append(sync)

                    if (conf50 >= 0 and (confCount > self.config.confCountLimit or confSpan > self.config.confSpanLimit)):
                        conf50Data.append(conf50)
                        if (PRStatus):
                            conf50Data_pr.append(conf50)

                    if (conf75 >= 0 and (confCount > self.config.confCountLimit or confSpan > self.config.confSpanLimit)):
                        conf75Data.append(conf75)
                        if (PRStatus):
                            conf75Data_pr.append(conf75)

                    if (conf90 >= 0 and (confCount > self.config.confCountLimit or confSpan > self.config.confSpanLimit)):
                        conf90Data.append(conf90)
                        if (PRStatus):
                            conf90Data_pr.append(conf90)

                    if (conf99 >= 0 and (confCount > self.config.confCountLimit or confSpan > self.config.confSpanLimit)):
                        conf99Data.append(conf99)
                        if (PRStatus):
                            conf99Data_pr.append(conf99)

                    if (confAve >= 0 and (confCount > self.config.confCountLimit or confSpan > self.config.confSpanLimit)):
                        confAveData.append(confAve)
                        if (PRStatus):
                            confAveData_pr.append(confAve)

                    if (memory > 0):
                        memoryData.append(memory)
                        if (PRStatus):
                            memoryData_pr.append(memory)

                    if (procTime > 0):
                        procTimeData.append(procTime)
                        if (PRStatus):
                            procTimeData_pr.append(procTime)

                    if (multiplier > 0):
                        multiplierData.append(multiplier)
                        if (PRStatus):
                            multiplierData_pr.append(multiplier)

                    # combined reps from monitors and telemetry data
                    nanoAccount = nanoNodeAccount
                    if (nanoAccount and nanoAccount != -1):
                        nanoAccount = nanoAccount.replace('xrb_', 'nano_')
                    supportedReps.append({'name': name, 'nanoNodeAccount': nanoAccount,
                                          'version': version, 'protocolVersion': protocolVersion, 'storeVendor': storeVendor, 'currentBlock': count, 'cementedBlocks': cemented,
                                          'unchecked': unchecked, 'numPeers': peers, 'confAve': confAve, 'confMedian': conf50, 'weight': weight, 'bps': bps, 'cps': cps,
                                          'memory': memory, 'procTime': procTime, 'multiplier': multiplier, 'supported': not fail, 'PR': PRStatus, 'isTelemetry': isTelemetryMatch,
                                          'bandwidthCap': bw, 'tsu': tsu})
                    fail = False

                except Exception as e:
                    self.log.warning(
                        time_log("Could not append supported rep. %r" % e))
                    pass

            else:
                self.log.warning(time_log("Empty json from API calls"))

        # all telemetry peers that was not matched already
        try:
            for teleRep in telemetryPeers:
                found = False
                for supRep in supportedReps:
                    if teleRep['account'] == supRep['nanoNodeAccount']:  # do not include this
                        found = True
                        break

                # do not include telemetry IPs that was found by the monitor path guessing
                tempIP = teleRep['ip']
                if tempIP != "":
                    if '[::ffff:' in tempIP:  # ipv4
                        tempIP = re.search('ffff:(.*)\]:', tempIP).group(1)

                    for ip in self.config.monitorIPExistArray:
                        if tempIP == ip:  # do not include this
                            found = True
                            break

                if not found:
                    # skip if the node is out of sync
                    if int(teleRep['block_count']) < self.config.minCount:
                        continue

                    # check if alias exist and use that instead of IP
                    aliasSet = False
                    for aliasAccount in self.config.aliases:
                        if not 'account' in aliasAccount or not 'alias' in aliasAccount:
                            continue
                        if aliasAccount['account'] == teleRep['account']:
                            ip = aliasAccount['alias']
                            if ip == '':
                                ip = 'No Name'
                            aliasSet = True
                            break

                    # extract ip
                    if not aliasSet:
                        if teleRep['ip'] != "":
                            if '[::ffff:' in teleRep['ip']:  # ipv4
                                ip = re.search(
                                    'ffff:(.*)\]:', teleRep['ip']).group(1)
                                ip = ip.split('.')[0] + \
                                    '.x.x.' + ip.split('.')[3]
                            else:  # ipv6
                                ip = '[' + re.search('\[(.*)\]:',
                                                     teleRep['ip']).group(1) + ']'
                        else:
                            ip = ""

                    tempRep = {'name': ip,
                               'nanoNodeAccount': teleRep['account'],
                               'version': teleRep['vendor_version'],
                               'protocolVersion': teleRep['protocol_version'],
                               'storeVendor': '',
                               'currentBlock': teleRep['block_count'],
                               'cementedBlocks': teleRep['cemented_count'],
                               'unchecked': teleRep['unchecked_count'],
                               'numPeers': teleRep['peer_count'],
                               'confAve': -1,
                               'confMedian': -1,
                               'weight': teleRep['weight'],
                               'bps': teleRep['bps'],
                               'cps': teleRep['cps'],
                               'memory': -1,
                               'procTime': teleRep['req_time'],
                               'multiplier': -1,
                               'supported': True,
                               'PR': teleRep['PR'],
                               'isTelemetry': True,
                               'bandwidthCap': teleRep['bandwidth_cap'],
                               'tsu': teleRep['tsu']}

                    telemetryReps.append(tempRep)
        except Exception as e:
            self.log.warning(
                time_log("Could not extract non matched telemetry reps. %r" % e))

        blockCountMedian = 0
        cementedMedian = 0
        uncheckedMedian = 0
        peersMedian = 0
        diffMedian = 0
        conf50Median = 0
        conf75Median = 0
        conf90Median = 0
        conf99Median = 0
        confAveMedian = 0
        memoryMedian = 0
        procTimeMedian = 0
        multiplierMedian = 0

        blockCountMax = 0
        cementedMax = 0
        uncheckedMax = 0
        peersMax = 0
        diffMax = 0
        memoryMax = 0
        procTimeMax = 0
        multiplierMax = 0

        blockCountMin = 0
        cementedMin = 0
        uncheckedMin = 0
        peersMin = 0
        confAveMin = 0
        memoryMin = 0
        procTimeMin = 0
        multiplierMin = 0

        telemetryCount = 0
        BPSMax = 0
        BPSMedian = 0
        BPSp75 = 0
        CPSMax = 0
        CPSMedian = 0
        CPSp75 = 0

        bwLimit1 = 0
        bwLimit10 = 0
        bwLimit25 = 0
        bwLimit50 = 0
        bwLimit75 = 0
        bwLimit90 = 0
        bwLimit99 = 0

        # PR ONLY
        blockCountMedian_pr = 0
        cementedMedian_pr = 0
        uncheckedMedian_pr = 0
        peersMedian_pr = 0
        diffMedian_pr = 0
        conf50Median_pr = 0
        conf75Median_pr = 0
        conf90Median_pr = 0
        conf99Median_pr = 0
        confAveMedian_pr = 0
        memoryMedian_pr = 0
        procTimeMedian_pr = 0
        multiplierMedian_pr = 0

        blockCountMax_pr = 0
        cementedMax_pr = 0
        uncheckedMax_pr = 0
        peersMax_pr = 0
        diffMax_pr = 0
        memoryMax_pr = 0
        procTimeMax_pr = 0
        multiplierMax_pr = 0

        blockCountMin_pr = 0
        cementedMin_pr = 0
        uncheckedMin_pr = 0
        peersMin_pr = 0
        confAveMin_pr = 0
        memoryMin_pr = 0
        procTimeMin_pr = 0
        multiplierMin_pr = 0

        telemetryCount_pr = 0
        BPSMax_pr = 0
        BPSMedian_pr = 0
        BPSp75_pr = 0
        CPSMax_pr = 0
        CPSMedian_pr = 0
        CPSp75_pr = 0

        bwLimit1_pr = 0
        bwLimit10_pr = 0
        bwLimit25_pr = 0
        bwLimit50_pr = 0
        bwLimit75_pr = 0
        bwLimit90_pr = 0
        bwLimit99_pr = 0

        statData = None

        # calculate number of telemetry peers
        try:
            for p in telemetryPeers:
                if (p['PR']):
                    telemetryCount_pr += 1
                else:
                    telemetryCount += 1
        except Exception as e:
            self.log.warning(
                time_log("Could not calculate number of telemetry peers. %r" % e))

        # non pr is the total combined number
        telemetryCount = telemetryCount + telemetryCount_pr

        try:
            if len(countData) > 0:
                blockCountMedian = int(median(countData, self.log))
                blockCountMax = int(max(countData))
                blockCountMin = int(min(countData))
                # Update the min allowed block count
                self.config.minCount = int(blockCountMax/2)

                # Calculate diff
                if (blockCountMax > 0):
                    diffMedian = blockCountMax - blockCountMedian
                    diffMax = blockCountMax - blockCountMin

            if len(cementedData) > 0:
                cementedMedian = int(median(cementedData, self.log))
                cementedMax = int(max(cementedData))
                cementedMin = int(min(cementedData))
            if len(uncheckedData) > 0:
                uncheckedMedian = int(median(uncheckedData, self.log))
                uncheckedMax = int(max(uncheckedData))
                uncheckedMin = int(min(uncheckedData))
            if len(peersData) > 0:
                peersMedian = int(median(peersData, self.log))
                peersMax = int(max(peersData))
                peersMin = int(min(peersData))
            if len(conf50Data) > 0:
                conf50Median = int(median(conf50Data, self.log))
            if len(conf75Data) > 0:
                conf75Median = int(median(conf75Data, self.log))
            if len(conf90Data) > 0:
                conf90Median = int(median(conf90Data, self.log))
            if len(conf99Data) > 0:
                conf99Median = int(median(conf99Data, self.log))
            if len(confAveData) > 0:
                confAveMedian = int(median(confAveData, self.log))
                confAveMin = int(min(confAveData))
            if len(memoryData) > 0:
                memoryMedian = int(median(memoryData, self.log))
                memoryMax = int(max(memoryData))
                memoryMin = int(min(memoryData))
            if len(procTimeData) > 0:
                procTimeMedian = int(median(procTimeData, self.log))
                procTimeMax = int(max(procTimeData))
                procTimeMin = int(min(procTimeData))
            if len(multiplierData) > 0:
                multiplierMedian = float(median(multiplierData, self.log))
                multiplierMax = float(max(multiplierData))
                multiplierMin = float(min(multiplierData))

            # treat bps and cps a bit different. the max must only be taken from the peer with max block count
            medianArray = []
            if len(bpsData) > 0:
                for data in bpsData:
                    medianArray.append(data[0])  # add the bps
                    # find the matching max block count and use that bps as max (even if it's technically not max). It's to avoid bootstrapping result
                    if (data[1] == blockCountMax):
                        BPSMax = data[0]

                BPSMedian = float(median(medianArray, self.log))
                BPSp75 = float(percentile(medianArray, 75))

            medianArray = []
            if len(cpsData) > 0:
                for data in cpsData:
                    medianArray.append(data[0])  # add the bps
                    # find the matching max block count and use that cps as max (even if it's technically not max). It's to avoid bootstrapping result
                    if (data[1] == cementedMax):
                        CPSMax = data[0]

                CPSMedian = float(median(medianArray, self.log))
                CPSp75 = float(percentile(medianArray, 75))

            # Bandwidth limit percentiles (replace 0 with 10Gbit/s because it count as unlimited)
            medianArray = []
            if len(bwData) > 0:
                for data in bwData:
                    if data == 0:
                        data = 1250000000
                    medianArray.append(data)
                bwLimit1 = int(percentile(medianArray, 1))
                bwLimit10 = int(percentile(medianArray, 10))
                bwLimit25 = int(percentile(medianArray, 25))
                bwLimit50 = int(percentile(medianArray, 50))
                bwLimit75 = int(percentile(medianArray, 75))
                bwLimit90 = int(percentile(medianArray, 90))
                bwLimit99 = int(percentile(medianArray, 99))

            # PR ONLY
            if len(countData_pr) > 0:
                blockCountMedian_pr = int(median(countData_pr, self.log))
                blockCountMax_pr = int(max(countData_pr))
                blockCountMin_pr = int(min(countData_pr))

                # Calculate diff
                if (blockCountMax_pr > 0):
                    diffMedian_pr = blockCountMax_pr - blockCountMedian_pr
                    diffMax_pr = blockCountMax_pr - blockCountMin_pr

            if len(cementedData_pr) > 0:
                cementedMedian_pr = int(median(cementedData_pr, self.log))
                cementedMax_pr = int(max(cementedData_pr))
                cementedMin_pr = int(min(cementedData_pr))
            if len(uncheckedData_pr) > 0:
                uncheckedMedian_pr = int(median(uncheckedData_pr, self.log))
                uncheckedMax_pr = int(max(uncheckedData_pr))
                uncheckedMin_pr = int(min(uncheckedData_pr))
            if len(peersData_pr) > 0:
                peersMedian_pr = int(median(peersData_pr, self.log))
                peersMax_pr = int(max(peersData_pr))
                peersMin_pr = int(min(peersData_pr))
            if len(conf50Data_pr) > 0:
                conf50Median_pr = int(median(conf50Data_pr, self.log))
            if len(conf75Data_pr) > 0:
                conf75Median_pr = int(median(conf75Data_pr, self.log))
            if len(conf90Data_pr) > 0:
                conf90Median_pr = int(median(conf90Data_pr, self.log))
            if len(conf99Data_pr) > 0:
                conf99Median_pr = int(median(conf99Data_pr, self.log))
            if len(confAveData_pr) > 0:
                confAveMedian_pr = int(median(confAveData_pr, self.log))
                confAveMin_pr = int(min(confAveData_pr))
            if len(memoryData_pr) > 0:
                memoryMedian_pr = int(median(memoryData_pr, self.log))
                memoryMax_pr = int(max(memoryData_pr))
                memoryMin_pr = int(min(memoryData_pr))
            if len(procTimeData_pr) > 0:
                procTimeMedian_pr = int(median(procTimeData_pr, self.log))
                procTimeMax_pr = int(max(procTimeData_pr))
                procTimeMin_pr = int(min(procTimeData_pr))
            if len(multiplierData_pr) > 0:
                multiplierMedian_pr = float(
                    median(multiplierData_pr, self.log))
                multiplierMax_pr = float(max(multiplierData_pr))
                multiplierMin_pr = float(min(multiplierData_pr))

            # treat bps and cps a bit different. the max must only be taken from the peer with max block count
            medianArray = []
            if len(bpsData_pr) > 0:
                for data in bpsData_pr:
                    medianArray.append(data[0])  # add the bps
                    # find the matching max block count and use that bps as max (even if it's technically not max). It's to avoid bootstrapping result
                    if (data[1] == blockCountMax_pr):
                        BPSMax_pr = data[0]

                BPSMedian_pr = float(median(medianArray, self.log))
                BPSp75_pr = float(percentile(medianArray, 75))

            medianArray = []
            if len(cpsData_pr) > 0:
                for data in cpsData_pr:
                    medianArray.append(data[0])  # add the bps
                    # find the matching max block count and use that bps as max (even if it's technically not max). It's to avoid bootstrapping result
                    if (data[1] == cementedMax_pr):
                        CPSMax_pr = data[0]

                CPSMedian_pr = float(median(medianArray, self.log))
                CPSp75_pr = float(percentile(medianArray, 75))

            # Bandwidth limit percentiles (replace 0 with 10Gbit/s because it count as unlimited)
            medianArray = []
            if len(bwData_pr) > 0:
                for data in bwData_pr:
                    if data == 0:
                        data = 1250000000
                    medianArray.append(data)
                bwLimit1_pr = int(percentile(medianArray, 1))
                bwLimit10_pr = int(percentile(medianArray, 10))
                bwLimit25_pr = int(percentile(medianArray, 25))
                bwLimit50_pr = int(percentile(medianArray, 50))
                bwLimit75_pr = int(percentile(medianArray, 75))
                bwLimit90_pr = int(percentile(medianArray, 90))
                bwLimit99_pr = int(percentile(medianArray, 99))

            # Write output file
            statData = {
                "blockCountMedian": int(blockCountMedian),
                "blockCountMax": int(blockCountMax),
                "blockCountMin": int(blockCountMin),
                "cementedMedian": int(cementedMedian),
                "cementedMax": int(cementedMax),
                "cementedMin": int(cementedMin),
                "uncheckedMedian": int(uncheckedMedian),
                "uncheckedMax": int(uncheckedMax),
                "uncheckedMin": int(uncheckedMin),
                "peersMedian": int(peersMedian),
                "peersMax": int(peersMax),
                "peersMin": int(peersMin),
                "diffMedian": float(diffMedian),
                "diffMax": float(diffMax),
                "memoryMedian": int(memoryMedian),
                "memoryMax": int(memoryMax),
                "memoryMin": int(memoryMin),
                "procTimeMedian": int(procTimeMedian),
                "procTimeMax": int(procTimeMax),
                "procTimeMin": int(procTimeMin),
                "multiplierMedian": float(multiplierMedian),
                "multiplierMax": float(multiplierMax),
                "multiplierMin": float(multiplierMin),
                "conf50Median": int(conf50Median),
                "conf75Median": int(conf75Median),
                "conf90Median": int(conf90Median),
                "conf99Median": int(conf99Median),
                "confAveMedian": int(confAveMedian),
                "confAveMin": int(confAveMin),
                "lenBlockCount": int(len(countData)),
                "lenCemented": int(len(cementedData)),
                "lenUnchecked": int(len(uncheckedData)),
                "lenPeers": int(len(peersData)),
                "lenConf50": int(len(conf50Data)),
                "lenMemory": int(len(memoryData)),
                "lenProcTime": int(len(procTimeData)),
                "lenMultiplier": int(len(multiplierData)),
                "monitorCount": monitorCount,
                "telemetryCount": telemetryCount,
                "BPSMax": BPSMax,
                "BPSMedian": BPSMedian,
                "BPSp75": BPSp75,
                "CPSMax": CPSMax,
                "CPSMedian": CPSMedian,
                "CPSp75": CPSp75,
                "bwLimit1": bwLimit1,
                "bwLimit10": bwLimit10,
                "bwLimit25": bwLimit25,
                "bwLimit50": bwLimit50,
                "bwLimit75": bwLimit75,
                "bwLimit90": bwLimit90,
                "bwLimit99": bwLimit99,

                # PR ONLY START
                "blockCountMedian_pr": int(blockCountMedian_pr), \
                "blockCountMax_pr": int(blockCountMax_pr), \
                "blockCountMin_pr": int(blockCountMin_pr), \
                "cementedMedian_pr": int(cementedMedian_pr), \
                "cementedMax_pr": int(cementedMax_pr), \
                "cementedMin_pr": int(cementedMin_pr), \
                "uncheckedMedian_pr": int(uncheckedMedian_pr), \
                "uncheckedMax_pr": int(uncheckedMax_pr), \
                "uncheckedMin_pr": int(uncheckedMin_pr), \
                "peersMedian_pr": int(peersMedian_pr), \
                "peersMax_pr": int(peersMax_pr), \
                "peersMin_pr": int(peersMin_pr), \
                "diffMedian_pr": float(diffMedian_pr), \
                "diffMax_pr": float(diffMax_pr), \
                "memoryMedian_pr": int(memoryMedian_pr), \
                "memoryMax_pr": int(memoryMax_pr), \
                "memoryMin_pr": int(memoryMin_pr), \
                "procTimeMedian_pr": int(procTimeMedian_pr), \
                "procTimeMax_pr": int(procTimeMax_pr), \
                "procTimeMin_pr": int(procTimeMin_pr), \
                "multiplierMedian_pr": float(multiplierMedian_pr), \
                "multiplierMax_pr": float(multiplierMax_pr), \
                "multiplierMin_pr": float(multiplierMin_pr), \
                "conf50Median_pr": int(conf50Median_pr), \
                "conf75Median_pr": int(conf75Median_pr), \
                "conf90Median_pr": int(conf90Median_pr), \
                "conf99Median_pr": int(conf99Median_pr), \
                "confAveMedian_pr": int(confAveMedian_pr), \
                "confAveMin_pr": int(confAveMin_pr), \
                "lenBlockCount_pr": int(len(countData_pr)), \
                "lenCemented_pr": int(len(cementedData_pr)), \
                "lenUnchecked_pr": int(len(uncheckedData_pr)), \
                "lenPeers_pr": int(len(peersData_pr)), \
                "lenConf50_pr": int(len(conf50Data_pr)), \
                "lenMemory_pr": int(len(memoryData_pr)), \
                "lenProcTime_pr": int(len(procTimeData_pr)), \
                "lenMultiplier_pr": int(len(multiplierData_pr)), \
                "monitorCount_pr": monitorCount_pr, \
                "telemetryCount_pr": telemetryCount_pr, \
                "BPSMax_pr": BPSMax_pr, \
                "BPSMedian_pr": BPSMedian_pr, \
                "BPSp75_pr": BPSp75_pr, \
                "CPSMax_pr": CPSMax_pr, \
                "CPSMedian_pr": CPSMedian_pr, \
                "CPSp75_pr": CPSp75_pr, \
                "bwLimit1_pr": bwLimit1_pr, \
                "bwLimit10_pr": bwLimit10_pr, \
                "bwLimit25_pr": bwLimit25_pr, \
                "bwLimit50_pr": bwLimit50_pr, \
                "bwLimit75_pr": bwLimit75_pr, \
                "bwLimit90_pr": bwLimit90_pr, \
                "bwLimit99_pr": bwLimit99_pr, \
                # PR ONLY END
                "self.config.pLatestVersionStat": self.config.pLatestVersionStat, \
                "self.config.pTypesStat": self.config.pTypesStat, \
                "self.config.pStakeTotalStat": self.config.pStakeTotalStat, \
                "self.config.pStakeRequiredStat": self.config.pStakeRequiredStat, \
                "self.config.pStakeLatestVersionStat": self.config.pStakeLatestVersionStat, \
                "pStakeOnline": self.config.latestOnlineWeight, \
                "lastUpdated": str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')), \
                "lastUpdatedUnix": str(time.time()), \
                "speedTest": "-1", \
            }

            # save to global vars used for pushing to blockchain later
            self.config.latestGlobalBlocks.append(
                {"time": time.time(), "data": statData['cementedMedian_pr']})
            self.config.latestGlobalPeers.append(
                {"time": time.time(), "data": statData['peersMedian_pr']})
            self.config.latestGlobalDifficulty.append(
                {"time": time.time(), "data": statData['multiplierMedian_pr']})

        except Exception as e:
            self.log.error(
                time_log('Could not create stat data. Error: %r' % e))
            pass

        try:
            if blockCountMedian > 0 and blockCountMax > 0 and statData is not None and supportedReps is not None and telemetryReps is not None:
                try:
                    with open(self.config.statFile, 'w') as outfile:
                        outfile.write(json.dumps(statData, indent=2))
                except Exception as e:
                    self.log.error(
                        time_log('Could not write stat data. Error: %r' % e))

                try:
                    # combine monitor list with telemetry list
                    combinedList = supportedReps + telemetryReps
                    with open(self.config.monitorFile, 'w') as outfile:
                        outfile.write(json.dumps(combinedList, indent=2))
                except Exception as e:
                    self.log.error(
                        time_log('Could not write monitor data. Error: %r' % e))

        except Exception as e:
            self.log.error(
                time_log('Could not write output data. Error: %r' % e))
            pass
