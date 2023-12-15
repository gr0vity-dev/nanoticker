import datetime
import math


def timeLog(msg):
    return str(datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')) + ": " + msg


def chunks(l, n):
    """Yield successive n-sized chunks from l"""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def percentile(data, percentile):
    n = len(data)
    p = n * percentile / 100
    if p.is_integer():
        return sorted(data)[int(p)]
    else:
        return sorted(data)[int(math.ceil(p)) - 1]

# Calculate the average value of the 50% middle percentile from a list


def median(lst, log):
    try:
        if lst == None or lst == []:
            return 0
        if len(lst) == 1:
            return lst[0]

        sortedLst = sorted(lst)
        lstLen = len(lst)
        index = (lstLen - 1) // 2

        # Do average of mid sub list
        if lstLen > 6:
            if (lstLen % 2):
                startIndex = index - (lstLen // 4)

            else:
                startIndex = index - (lstLen // 4) + 1

            endIndex = index + (lstLen // 4) + 1
            range = sortedLst[startIndex:endIndex]
            return sum(range) / len(range)  # average of the sub list

        # Do normal median
        else:
            if (lstLen % 2):
                return sortedLst[index]
            else:
                return (sortedLst[index] + sortedLst[index + 1])/2.0
    except Exception as e:
        log.warning(timeLog("Could not calculate median value. %r" % e))


def medianNormal(lst):
    sortedLst = sorted(lst)
    lstLen = len(lst)
    index = (lstLen - 1) // 2

    if (lstLen % 2):
        return sortedLst[index]
    else:
        return (sortedLst[index] + sortedLst[index + 1])/2.0
