#!/usr/bin/env python3

import os

from utils.plot_config import *
from utils.stats_report import *
from utils.plotters import *


from pathlib import Path
from argparse import ArgumentParser

CURRENT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
PROJECT_DIR = CURRENT_DIR.parent
PLOTS_DIR = PROJECT_DIR / "plots"


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


def main():
    parser = ArgumentParser(description="Plot PCAP stats reports")
    parser.add_argument("report", type=Path, help="Path to the stats report file (JSON)")
    args = parser.parse_args()

    report_file = args.report
    data = parse_report(report_file)
    plot_pkts_per_flow_cdf(report_file.stem, data.pkts_per_flow_cdf)


if __name__ == "__main__":
    main()
