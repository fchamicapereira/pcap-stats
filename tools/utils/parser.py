from typing import NewType, Union
from pathlib import Path

import re
import statistics
import itertools

from utils.heatmap import HeatmapData, Key, Values

Header = NewType("Header", list[str])
Data = NewType("Data", list[list[int | float]])


def parse_csv_elem(elem: str) -> Union[int, float]:
    if re.match(r"^[-\+]?\d+$", elem):
        return int(elem)

    try:
        return float(elem)
    except ValueError:
        # So, not an integer
        pass

    print(f"Unable to parse csv element {elem}")
    exit(1)


def csv_parser(file: Path) -> tuple[Header, Data]:
    assert file.exists()

    with open(str(file), "r") as f:
        lines = f.readlines()
        lines = [l.rstrip().split(",") for l in lines]

        header = Header(lines[0])
        rows = lines[1:]

        values = [[parse_csv_elem(elem) for elem in row] for row in rows]

        # Sort data by iteration (1st column)
        values = Data(sorted(values, key=lambda x: x[0]))

        return header, values


def aggregate_values(values: Data, x_elem: int, y_elem: int) -> list[tuple[float, float, float]]:
    new_values = []

    values = Data(sorted(values, key=lambda x: x[x_elem]))
    values_grouped = [list(v[1]) for v in itertools.groupby(values, key=lambda x: x[x_elem])]

    for vv in values_grouped:
        x_values = [v[x_elem] for v in vv]
        y_values = [v[y_elem] for v in vv]

        # Assert that they have the same x value
        assert len(set(x_values)) == 1

        x = x_values[0]
        y = y_values[0]
        yerr = 0

        if len(y_values) > 1:
            y = statistics.mean(y_values)
            yerr = statistics.stdev(y_values)

        new_values.append((x, y, yerr))

    return new_values


def parse_heatmap_data_file(file: Path) -> HeatmapData:
    data = HeatmapData()
    with open(file, "r") as f:
        for line in f.readlines():
            if line.startswith("#"):
                continue

            parts = line.split(",")

            keys = Key(
                float(parts[1]),
                int(parts[2]),
            )

            values = Values(
                int(parts[3]),
                int(parts[4]),
                int(parts[5]),
                int(parts[6]),
                int(parts[7]),
                int(parts[8]),
                int(parts[9]),
            )

            data.add(keys, values)

    return data
