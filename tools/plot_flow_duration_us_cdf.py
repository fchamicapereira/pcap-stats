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


def main():
    parser = ArgumentParser(description="Plot PCAP stats reports")
    parser.add_argument("report", type=Path, help="Path to the stats report file (JSON)")
    args = parser.parse_args()

    report_file = args.report
    data = parse_report(report_file)
    plot_flow_duration_us_cdf(report_file.stem, data.flow_duration_us_cdf)


if __name__ == "__main__":
    main()
