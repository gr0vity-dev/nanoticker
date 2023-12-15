
from src.rpc_requests import RpcWrapper
from src.config import Config
from src.helper import timeLog, chunks
import time
import re
import asyncio


async def peerSleep(startTime, runPeersEvery):
    sleep = runPeersEvery - (time.time() - startTime)
    if sleep < 0:
        sleep = 0
    await asyncio.sleep(sleep)


async def getPeers(config: Config, rpc_wrapper: RpcWrapper):
    log = config.log
    node_url = config.nodeUrl
    monitorIPExistArray = config.monitorIPExistArray

    while 1:
        startTime = time.time()  # to measure the loop speed
        pPeers = []
        pVersions = []
        pStakeTot = 0
        pStakeReq = 0
        supply = await rpc_wrapper.get_available_supply(node_url)

        # log.info(timeLog("Verifying peers"))
        monitorPaths = config.reps.copy()
        monitorIPPaths = {'ip': {}}
        monitorIPExistArray = {'ip': {}}

        # Grab connected peer IPs from the node
        params = {
            "action": "peers",
            "peer_details": True,
        }

        try:
            resp = await rpc_wrapper.get_regular_rpc(params)
            if 'peers' in resp[0]:
                peers = resp[0]['peers']
                for ipv6, value in peers.items():
                    if ipv6 == '':
                        continue
                    if '[::ffff:' in ipv6:  # ipv4
                        ip = re.search('ffff:(.*)\]:', ipv6).group(1)
                    else:  # ipv6
                        ip = '[' + re.search('\[(.*)\]:', ipv6).group(1) + ']'

                    if ip != "":
                        # Only try to find more monitors from peer IP in main network
                        if config.additional_monitors:
                            # Combine with previous list and ignore duplicates
                            exists = False
                            for url in monitorPaths:
                                path = 'http://'+ip
                                if path == url:
                                    exists = True
                                    break
                            if not exists:
                                monitorPaths.append(path)
                                monitorIPPaths[ip] = path

                            exists = False
                            for url in monitorPaths:
                                path = 'http://'+ip+'/nano'
                                if path == url:
                                    exists = True
                                    break
                            if not exists:
                                monitorPaths.append(path)
                                monitorIPPaths[ip] = path

                            exists = False
                            for url in monitorPaths:
                                path = 'http://'+ip+'/nanoNodeMonitor'
                                if path == url:
                                    exists = True
                                    break
                            if not exists:
                                monitorPaths.append(path)
                                monitorIPPaths[ip] = path

                            exists = False
                            for url in monitorPaths:
                                path = 'http://'+ip+'/monitor'
                                if path == url:
                                    exists = True
                                    break
                            if not exists:
                                monitorPaths.append(path)
                                monitorIPPaths[ip] = path

                        # Read protocol version and type
                        pVersions.append(value['protocol_version'])
                        pPeers.append(
                            {"ip": ipv6, "version": value["protocol_version"], "type": value["type"], "weight": 0, "account": ""})

        except Exception as e:
            log.warning(timeLog("Could not read peers from node RPC. %r" % e))
            await peerSleep(startTime, config.runPeersEvery)
            continue  # break out of main loop and try again next iteration

        # Grab voting weight stat
        params = {
            "action": "confirmation_quorum",
            "peer_details": True,
        }
        try:
            resp = await rpc_wrapper.get_regular_rpc(params)
            if 'peers_stake_total' in resp[0] and 'quorum_delta' in resp[0] and 'online_stake_total' in resp[0]:
                pStakeTot = resp[0]['peers_stake_total']
                pStakeReq = resp[0]['quorum_delta']
                config.latestOnlineWeight = int(resp[0]['online_stake_total']) / int(
                    1000000000000000000000000000000)  # used for calculating PR status

                # Find matching IP and include weight in original peer list
                for peer in resp[0]['peers']:
                    for i, cPeer in enumerate(pPeers):
                        if peer['ip'] == cPeer['ip'] and peer['ip'] != '':
                            # append the relevant PR stats here as well
                            weight = int(peer['weight']) / \
                                int(1000000000000000000000000000000)

                            # update previous vaule
                            pPeers[i] = dict(cPeer, **{"weight": weight})
                            continue

        except Exception as e:
            log.warning(timeLog("Could not read quorum from node RPC. %r" % e))
            pass

        # Grab supply
        params = {
            "action": "available_supply"
        }
        try:
            resp = await rpc_wrapper.get_regular_rpc(params)
            if 'available' in resp[0]:
                tempSupply = resp[0]['available']
                if int(tempSupply) > 0:  # To ensure no devision by zero
                    supply = tempSupply

        except Exception as e:
            log.warning(timeLog("Could not read supply from node RPC. %r" % e))
            pass

        # PERCENTAGE STATS
        try:
            maxVersion = 0
            versionCounter = 0
            if len(pVersions) > 0:
                maxVersion = int(max(pVersions))
                # Calculate percentage of nodes on latest version
                versionCounter = 0
                for version in pVersions:
                    if int(version) == maxVersion:
                        versionCounter += 1

            # Require at least 5 monitors to be at latest version to use as base, or use second latest version
            if versionCounter < 5 and len(pVersions) > 0:
                # extract second largest number by first removing duplicates
                simplified = list(set(pVersions))
                simplified.sort()
                if len(simplified) > 1:
                    maxVersion = int(simplified[-2])
                else:
                    maxVersion = int(simplified[0])
                versionCounter = 0
                for version in pVersions:
                    if int(version) == maxVersion:
                        versionCounter += 1

            if len(pVersions) > 0:
                config.pLatestVersionStat = versionCounter / \
                    int(len(pVersions)) * 100
            else:
                config.pLatestVersionStat = 0

            config.pStakeTotalStat = int(pStakeTot) / int(supply) * 100
            config.pStakeRequiredStat = int(pStakeReq) / int(supply) * 100

            # Calculate portion of weight and TCP in the latest versions
            combinedWeightInLatest = 0
            combinedTotalWeight = 0
            TCPInLatestCounter = 0
            for peer in pPeers:
                combinedTotalWeight = combinedTotalWeight + \
                    (int(peer['weight'])*int(1000000000000000000000000000000))
                if int(peer['version']) == int(maxVersion):
                    combinedWeightInLatest = combinedWeightInLatest + \
                        (int(peer['weight']) *
                         int(1000000000000000000000000000000))

                if (peer['type'] == 'tcp'):
                    TCPInLatestCounter += 1

            if (int(pStakeTot) > 0):
                config.pStakeLatestVersionStat = int(
                    combinedWeightInLatest) / int(combinedTotalWeight) * 100

            if len(pPeers) > 0:
                config.pTypesStat = TCPInLatestCounter / int(len(pPeers)) * 100
            else:
                config.pTypesStat = 0

        except Exception as e:
            log.warning(timeLog("Could not calculate weight stat. %r" % e))
            pass

        # Get monitors from Ninja API
        try:
            if config.ninjaMonitors == "":
                monitors = [{"monitor": {
                    "sync": 0, "url": "http://nl_genesis_monitor:80", "version": "0", "blocks": 0}, "account": ""}]
            else:
                monitors = rpc_wrapper.request_get(
                    config.ninjaMonitors, timeout=30)
            if len(monitors) > 0:
                for monitor in monitors:
                    try:
                        url = monitor['monitor']['url']
                        # Correct bad ending in some URLs like /api.php which will be added later
                        url = url.replace('/api.php', '')
                        if url[-1] == '/':  # ends with /
                            url = url[:-1]

                        # Ignore duplicates (IPs may still lead to same host name but that will be dealt with later)
                        exists = False
                        for path in monitorPaths:
                            if path == url:
                                exists = True
                                break
                        if not exists:
                            monitorPaths.append(url)
                    except:
                        log.warning(timeLog("Invalid Ninja monitor"))

        except Exception as e:
            pass
            # log.warning(timeLog("Could not read monitors from ninja. %r" %e))

        # Get aliases from URL
        if config.aliasUrl != '':
            try:
                config.aliases = rpc_wrapper.request_get(
                    config.aliasUrl, timeout=30)
            except Exception as e:
                pass
                # log.warning(timeLog("Could not read aliases from ninja. %r" %e))

        # Apply blacklist
        for i, node in enumerate(monitorPaths):
            for exl in config.blacklist:
                if node == exl:
                    del monitorPaths[i]
                    break

        # Verify all URLS
        validPaths = []
        repAccounts = []

        """Split URLS in max X concurrent requests"""
        for chunk in chunks(monitorPaths, config.maxURLRequests):
            tasks = []
            for path in chunk:
                if len(path) > 6:
                    if path[-4:] != '.htm':
                        tasks.append(asyncio.ensure_future(
                            rpc_wrapper.verify_monitor('%s/api.php' % path)))
                    else:
                        tasks.append(asyncio.ensure_future(
                            rpc_wrapper.verify_monitor(path)))
            try:
                await asyncio.gather(*tasks)

            except asyncio.TimeoutError as t:
                pass
                # log.warning(timeLog('Monitor Peer read timeout: %r' %t))

            for i, task in enumerate(tasks):
                try:
                    if task.result() is not None and task.result():
                        # Save valid peer urls
                        # Check for duplicate account (IP same as hostname)
                        exists = False
                        for account in repAccounts:
                            if task.result()[0] == account:
                                exists = True
                                break
                        if not exists:
                            validPaths.append(task.result()[1])
                            # Check if path exist among special IP paths
                            for key in monitorIPPaths:
                                if monitorIPPaths[key] == task.result()[1]:
                                    monitorIPExistArray[key] = {
                                        'account': task.result()[0]}
                        repAccounts.append(task.result()[0])

                except Exception as e:
                    pass

                finally:
                    if task.done() and not task.cancelled():
                        task.exception()  # this doesn't raise anything, just mark exception retrieved

        # Update the final list
        config.reps = validPaths.copy()
        # log.info(reps)

        await peerSleep(startTime, config.runPeersEvery)
