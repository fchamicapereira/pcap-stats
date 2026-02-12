#!/usr/bin/env python3

import os

from utils.plot_config import *

from msgspec.json import decode
from msgspec import Struct
from pathlib import Path
from typing import Literal
from argparse import ArgumentParser

import matplotlib.pyplot as plt

CURRENT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
PROJECT_DIR = CURRENT_DIR.parent
PLOTS_DIR = PROJECT_DIR / "plots"


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


def plot_cdf(
    pdf: str,
    values: list[float] | list[int],
    probabilities: list[float],
    xlabel: str,
    xmin: int | float,
    xmax: int | float,
    xticks: list[int] | list[float],
    xscale: Literal["linear", "log", "symlog", "logit"],
    xscale_base: int = 10,
):
    fig, ax = plt.subplots()

    if max(values) == 0:
        print(f"Skipping {pdf} plot, no data")
        return

    yticks = [i / 10 for i in range(0, 11, 2)]

    ax.set_xlabel(xlabel)
    ax.set_ylabel("CDF")

    ax.set_xlim(xmin=xmin, xmax=xmax)
    ax.set_ylim(ymin=0, ymax=1.0)

    if xscale != "linear":
        ax.set_xscale(xscale, base=xscale_base)

    ax.set_xticks(xticks)
    ax.set_yticks(yticks)

    ax.step(values, probabilities)

    fig.set_size_inches(width, height)
    fig.tight_layout(pad=0.1)

    print("-> ", pdf)

    plt.savefig(pdf)
    plt.close()


def plot_pkt_bytes_cdf(name: str, pkt_bytes_cdf: CDF):
    pdf = str(Path(PLOTS_DIR / f"{name}_pkt_bytes_cdf.pdf"))

    values = pkt_bytes_cdf.values
    probabilities = pkt_bytes_cdf.probabilities

    xlabel = "Packet bytes"
    xscale = "linear"
    xscale_base = 10

    if max(values) > 1600:
        xmin = 64
        xmax = max(values)
        xscale = "log"
        xscale_base = 2
        xticks = [64]
        while xticks[-1] < xmax:
            xticks.append(xticks[-1] * xscale_base)
    else:
        xmin = 0
        xmax = 1500
        xticks = [0, 250, 500, 750, 1000, 1250, 1500]

    plot_cdf(pdf, values, probabilities, xlabel, xmin, xmax, xticks, xscale, xscale_base)


def plot_pkts_per_flow_cdf(name: str, pkts_per_flow_cdf: CDF):
    pdf = str(Path(PLOTS_DIR / f"{name}_pkts_per_flow_cdf.pdf"))

    values = pkts_per_flow_cdf.values
    probabilities = pkts_per_flow_cdf.probabilities

    xlabel = "Packets/flow"
    xscale = "log"
    xscale_base = 10

    xmin = 1
    xmax = max(values)

    xticks = [1]
    while xticks[-1] < xmax:
        xticks.append(xticks[-1] * xscale_base)

    plot_cdf(pdf, values, probabilities, xlabel, xmin, xmax, xticks, xscale, xscale_base)


def plot_top_k_flows_cdf(name: str, top_k_flows_cdf: CDF):
    pdf = str(Path(PLOTS_DIR / f"{name}_top_k_flows_cdf.pdf"))

    max_value = max(top_k_flows_cdf.values)
    values = [100.0 * v / max_value for v in top_k_flows_cdf.values]
    probabilities = top_k_flows_cdf.probabilities

    xlabel = "Top-k flows (\\%)"
    xscale_base = 10

    xmax = 100

    if min(values) < 1:
        xscale = "log"
        xmin = min(values)
        xticks = [xscale_base ** math.floor(math.log(xmin, xscale_base))]
        while xticks[-1] < xmax:
            xticks.append(xticks[-1] * xscale_base)

    else:
        xscale = "linear"
        xmin = 0
        xticks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    plot_cdf(pdf, values, probabilities, xlabel, xmin, xmax, xticks, xscale, xscale_base)


def plot_top_k_flows_bytes_cdf(name: str, top_k_flows_bytes_cdf: CDF):
    pdf = str(Path(PLOTS_DIR / f"{name}_top_k_flows_bytes_cdf.pdf"))

    max_value = max(top_k_flows_bytes_cdf.values)
    values = [100.0 * v / max_value for v in top_k_flows_bytes_cdf.values]
    probabilities = top_k_flows_bytes_cdf.probabilities

    xlabel = "Top-k flows (bytes) (\\%)"
    xscale_base = 10

    xmax = 100

    if min(values) < 1:
        xscale = "log"
        xmin = min(values)
        xticks = [xscale_base ** math.floor(math.log(xmin, xscale_base))]
        while xticks[-1] < xmax:
            xticks.append(xticks[-1] * xscale_base)

    else:
        xscale = "linear"
        xmin = 0
        xticks = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    plot_cdf(pdf, values, probabilities, xlabel, xmin, xmax, xticks, xscale, xscale_base)


def plot_flow_duration_us_cdf(name: str, flow_duration_us_cdf: CDF):
    pdf = str(Path(PLOTS_DIR / f"{name}_fct_cdf.pdf"))

    values = [v / 1e6 for v in flow_duration_us_cdf.values]
    probabilities = flow_duration_us_cdf.probabilities

    xlabel = "Flow Completion Time (s)"
    xscale = "log"
    xscale_base = 10

    xmin = 1e-6
    xmax = max(values)
    xticks = [1e-6, 1e-4, 1e-2, 1e0, 1e2, 1e4, 1e6]

    plot_cdf(pdf, values, probabilities, xlabel, xmin, xmax, xticks, xscale, xscale_base)


def plot_flow_dts_us_cdf(name: str, flow_dts_us_cdf: CDF):
    pdf = str(Path(PLOTS_DIR / f"{name}_flow_ipt_cdf.pdf"))

    values = [v / 1e6 for v in flow_dts_us_cdf.values]
    probabilities = flow_dts_us_cdf.probabilities

    xlabel = "Flow inter-packet time (s)"
    xscale = "log"
    xscale_base = 10

    xmin = 1e-6
    xmax = max(values)
    xticks = [1e-6, 1e-4, 1e-2, 1e0, 1e2, 1e4, 1e6]

    plot_cdf(pdf, values, probabilities, xlabel, xmin, xmax, xticks, xscale, xscale_base)


def plot(name: str, report: StatsReport):
    plot_pkt_bytes_cdf(name, report.pkt_bytes_cdf)
    plot_pkts_per_flow_cdf(name, report.pkts_per_flow_cdf)
    plot_top_k_flows_cdf(name, report.top_k_flows_cdf)
    plot_top_k_flows_bytes_cdf(name, report.top_k_flows_bytes_cdf)
    plot_flow_duration_us_cdf(name, report.flow_duration_us_cdf)
    plot_flow_dts_us_cdf(name, report.flow_dts_us_cdf)


def main():
    parser = ArgumentParser(description="Plot PCAP stats reports")
    parser.add_argument("report", type=Path, help="Path to the stats report file (JSON)")
    args = parser.parse_args()

    report_file = args.report
    data = parse_report(report_file)
    plot(report_file.stem, data)


if __name__ == "__main__":
    main()
