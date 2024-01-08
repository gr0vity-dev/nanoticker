# Default starting node list. Beta net
def get_reps(env):
    if env.lower() in ("dev", "develop", "local"):
        return repsInitD
    elif env.lower() in ("beta"):
        return repsInitB
    elif env.lower() in ("live", "main"):
        return repsInitM


def get_blacklist(env):
    if env.lower() in ("dev", "develop", "local"):
        return blacklistD
    elif env.lower() in ("beta"):
        return blacklistB
    elif env.lower() in ("live", "main"):
        return blacklistM


repsInitD = [
    'http://nl_genesis_monitor:80',
    'http://nl_pr1:80',
    'http://nl_pr2:80',
    'http://nl_node3:80',
    'http://localhost:46004',
    'http://localhost:46005',
    'http://localhost:46006',
    'http://localhost:46007',
    'http://localhost:46008',
    'http://localhost:46009',
    'http://localhost:46010',
    'http://localhost:46011',
    'http://localhost:46012',
    'http://localhost:46013',
    'http://localhost:46014',
    'http://localhost:46015',
    'http://localhost:46016',
    'http://localhost:46017',
    'http://localhost:46018',
    'http://localhost:46019',
    'http://localhost:46020',
    'http://localhost:46021',
    'http://localhost:46022',
    'http://localhost:46023',
    'http://localhost:46024',
    'http://localhost:46025',
    'http://localhost:46026',
    'http://localhost:46027',
    'http://localhost:46028',
    'http://localhost:46029',
    'http://localhost:46030',
]

repsInitB = [
    'https://monitor.bnano.info',
]
# Default starting node list. Main net
repsInitM = [
    'https://nanode21.cloud',
    'http://nano-node-01.scheler.io',
    'https://monitor.nanoticker.info',
    'https://warai.me',
    'https://getcanoe.io/api.php',
    'https://nano.gray.network',
    'https://nanoskynode.com',
    'http://nanotipbot.com/nanoNodeMonitor',
    'http://167.99.228.57',
    'https://nanomakonode.com',
    'https://node.nano.trade',
    'https://nano.pagcripto.com.br',
    'https://node.polyrun.app',
]

# Black lists (excluded from NanoTicker)
blacklistD = []
blacklistB = []
blacklistM = [
    'http://node.nanologin.com',
]
