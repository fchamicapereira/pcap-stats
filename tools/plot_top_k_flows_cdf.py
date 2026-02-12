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


def main():
    parser = ArgumentParser(description="Plot PCAP stats reports")
    parser.add_argument("report", type=Path, help="Path to the stats report file (JSON)")
    args = parser.parse_args()

    report_file = args.report
    data = parse_report(report_file)
    plot_top_k_flows_cdf(report_file.stem, data.top_k_flows_cdf)


if __name__ == "__main__":
    main()
