from pathlib import Path

from utils.parser import Data, aggregate_values, csv_parser

MAX_XPUT_PPS_SWITCH_ASIC = 117_191_634
MAX_XPUT_PPS_SWITCH_CPU = 120_736

MAX_STABLE_CPU_RATIO = 0.002

def get_estimator_data(csv: Path) -> tuple[list[float], list[float], list[float]]:
    assert csv.exists()
    raw_data = csv_parser(csv)[1]

    data = Data([])
    for d in raw_data:
        i, target_cpu_ratio, asic_pkts, cpu_pkts, _, xput_pps = d
        real_cpu_ratio = cpu_pkts / asic_pkts

        # Experiment limitations.
        # E.g. the target CPU ratio might be 0.6, but 1/0.6 = 1.(6) ~ 1 = 1/1
        if target_cpu_ratio != 1 and real_cpu_ratio == 1:
            target_cpu_ratio = 1
        else:
            acceptable_error = 0.25 # 25%
            if target_cpu_ratio != 0:
                error = abs(target_cpu_ratio - real_cpu_ratio) / target_cpu_ratio
                assert error <= acceptable_error

        data.append([ i, real_cpu_ratio, xput_pps ])
    
    x_elem = 1 # cpu ratio
    y_elem = 2 # Throughput pps column    
    agg_values = aggregate_values(data, x_elem, y_elem)

    x    = [ v[0] for v in agg_values ]
    y    = [ v[1] for v in agg_values ]
    yerr = [ v[2] for v in agg_values ]

    return x, y, yerr

def xput_estimator_pps(
    r: float,
    processing_latency: float = 0,
) -> float:
    d = 0.0001
    e = 5
    # C = MAX_STABLE_CPU_RATIO * (10**(-processing_latency * d))
    C = MAX_STABLE_CPU_RATIO
    tA = MAX_XPUT_PPS_SWITCH_ASIC
    tC = MAX_XPUT_PPS_SWITCH_CPU

    if r <= C:
        return tA
    
    ########################
    # Model: a*(1-r) + b*r
    ########################
    # return tA * (1 - (r - C) / (1 - C)) + tC * (r - C) / (1 - C)

    ########################
    # Model: a*log(b*r+c) + d
    ########################
    # if r == 1: return tC
    # a = tC-tA
    # b = (1-1/math.e)/(1-C)
    # c = ((1/math.e)-C)/(1-C)
    # d = tC
    # return a*math.log(b*r+c) + d

    ########################
    # Model: a/r + b
    ########################
    # a = (tA-tC)*(C/(1-C))
    # b = tC-a
    # return (a/r)+b

    ########################
    # Model: a/r (assuming C ~ tC/tA)
    ########################
    # return tC / r

    # ---------------------------------------------------------
    #            |                              |
    #            | SUCCESSFUL MODELS START HERE |
    #            V                              V
    # ---------------------------------------------------------

    ########################
    # Model: 1 / (a*r + b)
    ########################
    # b = (1/(1-C))*((tC-C*tA)/(tA*tC))
    # a = 1/tC - b
    # return 1 / (a*r + b)

    ########################
    # Model: a / (r + b)
    ########################
    b = (C-(tC/tA))/((tC/tA)-1)
    a = tA * (C + b)
    return a / (r + b)

def estimate_xput_pps(
    cpu_ratios: list[float],
    processing_latency: float = 0,
) -> list[float]:
    estimates = []
    for cpu_ratio in cpu_ratios:
        assert cpu_ratio >= 0 and cpu_ratio <= 1
        estimation = xput_estimator_pps(cpu_ratio, processing_latency)
        estimates.append(estimation)
    return estimates
