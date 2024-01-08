
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


async def _process_monitor_paths(monitorPaths, rpc_wrapper: RpcWrapper, repAccounts, validPaths, monitorIPPaths, monitorIPExistArray):
    # Create a list of tasks
    tasks = [rpc_wrapper.verify_monitor(path) for path in monitorPaths]

    # Run tasks in parallel
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Process the results
    for result, path in zip(results, monitorPaths):
        if isinstance(result, Exception):
            # Handle exception (e.g., log it)
            continue

        if result:
            # Check for duplicate account
            if result[0] not in repAccounts:
                validPaths.append(result[1])
                repAccounts.append(result[0])

                # Check if path exists among special IP paths
                if result[1] in monitorIPPaths.values():
                    for key, value in monitorIPPaths.items():
                        if value == result[1]:
                            monitorIPExistArray[key] = {'account': result[0]}
                            break


def _calculate_version_statistics(config: Config, pVersions, pStakeTot, supply, pStakeReq, pPeers):
    try:
        total_nodes = len(pVersions)
        if total_nodes > 0:
            # Calculate the frequency of each version
            version_frequencies = {}
            for version in pVersions:
                version = int(version)
                version_frequencies[version] = version_frequencies.get(
                    version, 0) + 1

            # Determine the latest version based on the 10% threshold
            latest_version = None
            for version, count in version_frequencies.items():
                if count / total_nodes >= 0.10 and (latest_version is None or version > latest_version):
                    latest_version = version

            # Calculate percentage of nodes on latest version
            versionCounter = version_frequencies.get(latest_version, 0)
            config.pLatestVersionStat = versionCounter / total_nodes * 100
        else:
            config.pLatestVersionStat = 0

        # Calculate other statistics
        config.pStakeTotalStat = int(
            pStakeTot) / int(supply) * 100 if supply else 0
        config.pStakeRequiredStat = int(
            pStakeReq) / int(supply) * 100 if supply else 0

        # Calculate portion of weight and TCP in the latest versions
        combinedWeightInLatest = sum(int(peer['weight']) for peer in pPeers if int(
            peer['version']) == latest_version) if latest_version is not None else 0
        combinedTotalWeight = sum(int(peer['weight']) for peer in pPeers)
        TCPInLatestCounter = sum(1 for peer in pPeers if peer['type'] == 'tcp')

        if combinedTotalWeight > 0:
            config.pStakeLatestVersionStat = combinedWeightInLatest / combinedTotalWeight * 100
        if total_nodes > 0:
            config.pTypesStat = TCPInLatestCounter / total_nodes * 100
        else:
            config.pTypesStat = 0

    except Exception as e:
        config.log.warning(f"Could not calculate version statistics. {e}")


async def getPeers(config: Config, rpc_wrapper: RpcWrapper):
    log = config.log
    monitorIPExistArray = config.monitorIPExistArray

    while 1:
        startTime = time.time()  # to measure the loop speed
        pPeers = []
        pVersions = []
        pStakeTot = 0
        pStakeReq = 0
        supply = await rpc_wrapper.get_available_supply()

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
                            base_path = 'http://' + ip
                            suffixes = ['', '/nano',
                                        '/nanoNodeMonitor', '/monitor']

                            for suffix in suffixes:
                                path = base_path + suffix
                                if path not in monitorPaths:
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

        # Assuming your_class_instance is an instance of YourClassName
        _calculate_version_statistics(
            config, pVersions, pStakeTot, supply, pStakeReq, pPeers)

        # # PERCENTAGE STATS
        # try:
        #     maxVersion = 0
        #     versionCounter = 0
        #     if len(pVersions) > 0:
        #         maxVersion = int(max(pVersions))
        #         # Calculate percentage of nodes on latest version
        #         versionCounter = 0
        #         for version in pVersions:
        #             if int(version) == maxVersion:
        #                 versionCounter += 1

        #     # Require at least 5 monitors to be at latest version to use as base, or use second latest version
        #     if versionCounter < 5 and len(pVersions) > 0:
        #         # extract second largest number by first removing duplicates
        #         simplified = list(set(pVersions))
        #         simplified.sort()
        #         if len(simplified) > 1:
        #             maxVersion = int(simplified[-2])
        #         else:
        #             maxVersion = int(simplified[0])
        #         versionCounter = 0
        #         for version in pVersions:
        #             if int(version) == maxVersion:
        #                 versionCounter += 1

        #     if len(pVersions) > 0:
        #         config.pLatestVersionStat = versionCounter / \
        #             int(len(pVersions)) * 100
        #     else:
        #         config.pLatestVersionStat = 0

        #     config.pStakeTotalStat = int(pStakeTot) / int(supply) * 100
        #     config.pStakeRequiredStat = int(pStakeReq) / int(supply) * 100

        #     # Calculate portion of weight and TCP in the latest versions
        #     combinedWeightInLatest = 0
        #     combinedTotalWeight = 0
        #     TCPInLatestCounter = 0
        #     for peer in pPeers:
        #         combinedTotalWeight = combinedTotalWeight + \
        #             (int(peer['weight'])*int(1000000000000000000000000000000))
        #         if int(peer['version']) == int(maxVersion):
        #             combinedWeightInLatest = combinedWeightInLatest + \
        #                 (int(peer['weight']) *
        #                  int(1000000000000000000000000000000))

        #         if (peer['type'] == 'tcp'):
        #             TCPInLatestCounter += 1

        #     if (int(pStakeTot) > 0):
        #         config.pStakeLatestVersionStat = int(
        #             combinedWeightInLatest) / int(combinedTotalWeight) * 100

        #     if len(pPeers) > 0:
        #         config.pTypesStat = TCPInLatestCounter / int(len(pPeers)) * 100
        #     else:
        #         config.pTypesStat = 0

        # except Exception as e:
        #     log.warning(timeLog("Could not calculate weight stat. %r" % e))
        #     pass

        # Get monitors from Ninja API
        try:
            if config.query_reps == "":
                monitors = [{"monitor": {
                    "sync": 0, "url": "http://nl_genesis_monitor:80", "version": "0", "blocks": 0}, "account": ""}]
            else:
                monitors = await rpc_wrapper.request_post(
                    config.query_reps[0], config.query_reps[1], timeout=30)
            if len(monitors) > 0:
                for monitor in monitors:
                    try:
                        url = monitor['website']
                        if url is None:
                            continue
                        # # Correct bad ending in some URLs like /api.php which will be added later
                        # url = url.replace('/api.php', '')
                        # if url[-1] == '/':  # ends with /
                        #     url = url[:-1]

                        monitorPaths.append(url)
                    except:
                        log.warning(timeLog("Invalid Ninja monitor"))

        except Exception as e:
            pass

        # Get aliases from URL        if config.aliasUrl != '':
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

        await _process_monitor_paths(monitorPaths, rpc_wrapper, repAccounts, validPaths, monitorIPPaths, monitorIPExistArray)

        # Update the final list
        config.reps = validPaths.copy()
        # log.info(reps)

        await peerSleep(startTime, config.runPeersEvery)
