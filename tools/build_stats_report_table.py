#!/usr/bin/env python3

import os

from utils.stats_report import *
from prettytable import PrettyTable
from humanize import precisedelta
from statistics import mean, stdev
from pathlib import Path
from argparse import ArgumentParser

CURRENT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
PROJECT_DIR = CURRENT_DIR.parent
PLOTS_DIR = PROJECT_DIR / "plots"


def build_table(name: str, report: StatsReport):
    assert len(report.epochs) > 0, "Report must contain at least one epoch"

    avg_bytes_per_pkt = report.total_bytes / report.total_pkts
    total_bytes_on_the_write = report.total_pkts * 20 + report.total_bytes
    avg_packet_rate_bps = (report.total_bytes * 8) / ((report.end_utc_ns - report.start_utc_ns) / 1e9)
    avg_packet_rate_pps = report.total_pkts / ((report.end_utc_ns - report.start_utc_ns) / 1e9)
    elapsed_sec = (report.end_utc_ns - report.start_utc_ns) / 1e9
    avg_epoch_duration = elapsed_sec / len(report.epochs)
    avg_churn_fpm = (mean(epoch.new_flows for epoch in report.epochs) / avg_epoch_duration) * 60
    stdev_churn_fpm = (stdev(epoch.new_flows for epoch in report.epochs) / avg_epoch_duration) * 60
    avg_new_flows_per_epoch = mean(epoch.new_flows for epoch in report.epochs)
    stdev_new_flows_per_epoch = stdev(epoch.new_flows for epoch in report.epochs)
    avg_concurrent_flows_per_epoch = mean(epoch.concurrent_flows for epoch in report.epochs)
    stdev_concurrent_flows_per_epoch = stdev(epoch.concurrent_flows for epoch in report.epochs)

    txt = str(Path(PLOTS_DIR / f"{name}.txt"))

    table = PrettyTable()
    table.header = False
    table.align = "l"
    table.title = f"Report for {name}"

    table.add_row(["Total pkts", f"{report.total_pkts:,}"])
    table.add_row(["Total pkt bytes", f"{report.total_bytes:,} bytes"])
    table.add_row(["Avg pkt size", f"{avg_bytes_per_pkt:,.0f} bytes"])
    table.add_row(["Bytes on the wire", f"{total_bytes_on_the_write:,} bytes"])
    table.add_row(["Packet rate", f"{avg_packet_rate_bps:,.0f} bps ({avg_packet_rate_pps:,.0f} pps)"])
    table.add_row(["Elapsed", precisedelta(elapsed_sec, minimum_unit="microseconds")])
    table.add_row(["Avg epoch duration", precisedelta(avg_epoch_duration, minimum_unit="microseconds")])
    table.add_row(["Epochs", f"{len(report.epochs):,}"])
    table.add_row(["Avg churn", f"{avg_churn_fpm:,.0f} flows/min"])
    table.add_row(["Churn stdev", f"{stdev_churn_fpm:,.0f} flows/min"])
    table.add_row(["Avg new flows per epoch", f"{avg_new_flows_per_epoch:,.0f}"])
    table.add_row(["Stdev new flows per epoch", f"{stdev_new_flows_per_epoch:,.0f}"])
    table.add_row(["Avg concurrent flows per epoch", f"{avg_concurrent_flows_per_epoch:,.0f}"])
    table.add_row(["Stdev concurrent flows per epoch", f"{stdev_concurrent_flows_per_epoch:,.0f}"])

    with open(txt, "w") as f:
        f.write(str(table))


def main():
    parser = ArgumentParser(description="Build PCAP stats reports table")
    parser.add_argument("report", type=Path, help="Path to the stats report file (JSON)")
    args = parser.parse_args()

    report_file = args.report
    data = parse_report(report_file)
    build_table(report_file.stem, data)


if __name__ == "__main__":
    main()
