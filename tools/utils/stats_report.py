from pathlib import Path
from msgspec import Struct
from msgspec.json import decode


class CDF(Struct):
    values: list[int]
    probabilities: list[float]


class StatsReport(Struct):
    start_utc_ns: int
    end_utc_ns: int
    total_pkts: int
    tcpudp_pkts: int
    pkt_bytes_avg: float
    pkt_bytes_stdev: float
    pkt_bytes_cdf: CDF
    total_flows: int
    total_symm_flows: int
    pkts_per_flow_avg: float
    pkts_per_flow_stdev: float
    pkts_per_flow_cdf: CDF
    top_k_flows_cdf: CDF
    top_k_flows_bytes_cdf: CDF
    flow_duration_us_avg: float
    flow_duration_us_stdev: float
    flow_duration_us_cdf: CDF
    flow_dts_us_avg: float
    flow_dts_us_stdev: float
    flow_dts_us_cdf: CDF


def parse_report(file: Path) -> StatsReport:
    print(f"Parsing report: {file}")
    assert file.exists()
    with open(file, "rb") as f:
        report = decode(f.read(), type=StatsReport)
        return report
