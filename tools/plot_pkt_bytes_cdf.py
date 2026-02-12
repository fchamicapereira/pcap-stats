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


def main():
    parser = ArgumentParser(description="Plot PCAP stats reports")
    parser.add_argument("report", type=Path, help="Path to the stats report file (JSON)")
    args = parser.parse_args()

    report_file = args.report
    data = parse_report(report_file)
    plot_pkt_bytes_cdf(report_file.stem, data.pkt_bytes_cdf)


if __name__ == "__main__":
    main()
