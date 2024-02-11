
from src.rpc_requests import RpcWrapper
from src.config import Config
from src.helper import time_log
import time
import re
import asyncio


async def peer_sleep(start_time, interval):
    end_time = time.time()
    await asyncio.sleep(max(0, interval - (end_time - start_time)))


async def get_peer_ip(ipv6):
    if '[::ffff:' in ipv6:  # ipv4
        return re.search('ffff:(.*)\]:', ipv6).group(1)
    else:  # ipv6
        return '[' + re.search('\[(.*)\]:', ipv6).group(1) + ']'


async def get_peers_from_node_rpc(rpc_wrapper: RpcWrapper, config: Config, monitor_paths, p_versions, p_peers):
    params = {"action": "peers", "peer_details": True}
    try:
        resp = await rpc_wrapper.get_regular_rpc(params)
        if 'peers' in resp[0]:
            await process_peers(resp[0]['peers'], config, monitor_paths, p_versions, p_peers)
    except Exception as e:
        config.log.warning(
            time_log(f"Could not read peers from node RPC. {e}"))
        return False
    return True


async def process_peers(peers, config: Config, monitor_paths, p_versions, p_peers):
    for ipv6, value in peers.items():
        if ipv6 == '':
            continue
        ip = await get_peer_ip(ipv6)
        if ip != "":
            # Only try to find more monitors from peer IP in main network
            if config.additional_monitors:
                await update_monitor_paths(ip, monitor_paths)
            p_versions.append(value['protocol_version'])
            p_peers.append(
                {"ip": ipv6, "version": value["protocol_version"], "type": value["type"], "weight": 0, "account": ""})


async def update_monitor_paths(ip, monitor_paths):
    base_path = 'http://' + ip
    suffixes = ['', '/nano', '/nanoNodeMonitor', '/monitor']
    for suffix in suffixes:
        path = base_path + suffix
        if path not in monitor_paths:
            monitor_paths.append(path)


async def get_voting_weight_stat(rpc_wrapper: RpcWrapper, config: Config, p_peers):
    p_stake_tot = 0
    p_stake_req = 0
    params = {"action": "confirmation_quorum", "peer_details": True}
    try:
        resp = await rpc_wrapper.get_regular_rpc(params)
        if 'peers_stake_total' in resp[0] and 'quorum_delta' in resp[0] and 'online_stake_total' in resp[0]:
            p_stake_tot = resp[0]['peers_stake_total']
            p_stake_req = resp[0]['quorum_delta']
            config.latestOnlineWeight = int(
                resp[0]['online_stake_total']) / int(1000000000000000000000000000000)
            for peer in resp[0]['peers']:
                await update_peer_weights(peer, p_peers)
    except Exception as e:
        config.log.warning(
            time_log(f"Could not read quorum from node RPC. {e}"))
    return p_stake_tot, p_stake_req


async def update_peer_weights(peer, p_peers):
    for i, c_peer in enumerate(p_peers):
        if peer['ip'] == c_peer['ip'] and peer['ip'] != '':
            weight = int(peer['weight']) / int(1000000000000000000000000000000)
            p_peers[i] = dict(c_peer, **{"weight": weight})


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
            pStakeTot) / int(supply[0]) * 100 if supply else 0
        config.pStakeRequiredStat = int(
            pStakeReq) / int(supply[0]) * 100 if supply else 0

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


async def get_reps_from_nano_to(rpc_wrapper, config: Config, monitor_paths):
    try:
        if config.query_reps == "":
            monitors = [{"monitor": {"sync": 0, "website": "http://nl_genesis_monitor:80",
                                     "version": "0", "blocks": 0}, "account": ""}]
        else:
            monitors = await rpc_wrapper.request_post(config.query_reps[0], config.query_reps[1], timeout=30)

        for monitor in monitors:
            url = monitor.get('website', None)
            if url and url not in monitor_paths:
                monitor_paths.append(url)
    except Exception as e:
        config.log.warning(
            time_log("Error getting reps from nano.to: " + str(e)))


async def apply_blacklist(monitor_paths, config):
    # Converting to a set for efficient lookup
    blacklist = set(config.blacklist)
    monitor_paths = [path for path in monitor_paths if path not in blacklist]
    return monitor_paths


async def getPeers(config: Config, rpc_wrapper: RpcWrapper):
    while True:
        start_time = time.time()
        p_peers = []
        p_versions = []
        monitor_paths = config.reps.copy()
        valid_paths = []
        rep_accounts = []

        supply = await rpc_wrapper.get_available_supply()

        if not await get_peers_from_node_rpc(rpc_wrapper, config, monitor_paths, p_versions, p_peers):
            await peer_sleep(start_time, config.interval_get_peer)
            continue

        p_stake_tot, p_stake_req = await get_voting_weight_stat(rpc_wrapper, config, p_peers)

        await get_reps_from_nano_to(rpc_wrapper, config, monitor_paths)
        monitor_paths = await apply_blacklist(monitor_paths, config)

        # Call to _process_monitor_paths
        await _process_monitor_paths(monitor_paths, rpc_wrapper, rep_accounts, valid_paths, {}, {})

        # Update the final list
        config.reps = valid_paths.copy()

        # Call to _calculate_version_statistics
        _calculate_version_statistics(
            config, p_versions, p_stake_tot, supply, p_stake_req, p_peers)

        await peer_sleep(start_time, config.interval_get_peer)
