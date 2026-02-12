from utils.plot_config import *

import matplotlib.pyplot as plt

from typing import Literal


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
