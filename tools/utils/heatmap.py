from utils.values import Values

import statistics

from utils.util import *
from utils.plot_config import *
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from matplotlib import colormaps

TPUT_GBPS_MIN = 0
TPUT_GBPS_MAX = 1600

TPUT_MPPS_MIN = 0
TPUT_MPPS_MAX = 2500


@dataclass(frozen=True)
class Key:
    s: float
    churn_fpm: int


class HeatmapData:
    def __init__(self):
        self.raw_data: dict[Key, list[Values]] = {}

    def add(self, key: Key, values: Values):
        if key not in self.raw_data:
            self.raw_data[key] = []
        self.raw_data[key].append(values)

    def get(self, key: Key) -> list[Values]:
        assert key in self.raw_data, f"Key {key} not found in heatmap data."
        return self.raw_data[key]

    def filter(self, keys: list[Key]):
        new_heatmap_data = HeatmapData()
        for key, values in self.raw_data.items():
            if key not in keys:
                continue
            for value in values:
                new_heatmap_data.add(key, value)
        return new_heatmap_data

    def get_raw(self) -> dict[Key, list[Values]]:
        return self.raw_data

    def get_keys(self) -> list[Key]:
        return list(self.raw_data.keys())

    def get_values(self, key: Key) -> list[Values]:
        return self.raw_data[key]

    def get_avg_values(self) -> dict[Key, Values]:
        data: dict[Key, Values] = {}
        for key in self.raw_data.keys():
            if len(self.raw_data[key]) == 1:
                data[key] = self.raw_data[key][0]
            else:
                data[key] = Values(
                    statistics.mean([x.requested_bps for x in self.raw_data[key]]),
                    statistics.mean([x.pktgen_bps for x in self.raw_data[key]]),
                    statistics.mean([x.pktgen_pps for x in self.raw_data[key]]),
                    statistics.mean([x.dut_ingress_bps for x in self.raw_data[key]]),
                    statistics.mean([x.dut_ingress_pps for x in self.raw_data[key]]),
                    statistics.mean([x.dut_egress_bps for x in self.raw_data[key]]),
                    statistics.mean([x.dut_egress_pps for x in self.raw_data[key]]),
                )

        return data

    def get_stdev_values(self) -> dict[Key, Values]:
        data: dict[Key, Values] = {}
        for key in self.raw_data.keys():
            if len(self.raw_data[key]) == 1:
                data[key] = Values()
            else:
                data[key] = Values(
                    statistics.stdev([x.requested_bps for x in self.raw_data[key]]),
                    statistics.stdev([x.pktgen_bps for x in self.raw_data[key]]),
                    statistics.stdev([x.pktgen_pps for x in self.raw_data[key]]),
                    statistics.stdev([x.dut_ingress_bps for x in self.raw_data[key]]),
                    statistics.stdev([x.dut_ingress_pps for x in self.raw_data[key]]),
                    statistics.stdev([x.dut_egress_bps for x in self.raw_data[key]]),
                    statistics.stdev([x.dut_egress_pps for x in self.raw_data[key]]),
                )

        return data


def plot_bps(data: HeatmapData, file: Path):
    avg_data = data.get_avg_values()
    keys = avg_data.keys()
    all_s = sorted(set([key.s for key in keys]))
    all_churn = sorted(set([key.churn_fpm for key in keys]))
    churn_labels = [whole_number_to_label(churn) for churn in all_churn]
    fig, axs = plt.subplots(math.ceil(len(all_s) / 2), 2)

    for i in range(len(all_s)):
        ax = axs[int(i / 2), i % 2]
        s = all_s[i]

        ax.set_title(f"Zipf parameter: {s:.2f}")

        avg_tput_gbps = [avg_data[Key(s, churn)].dut_egress_bps / 1e9 for churn in all_churn]
        stdev_tput_gbps = [data.get_stdev_values()[Key(s, churn)].dut_egress_bps / 1e9 for churn in all_churn]

        ax.errorbar(churn_labels, avg_tput_gbps, yerr=stdev_tput_gbps, fmt="none", capsize=capsize, markeredgewidth=markeredgewidth, elinewidth=elinewidth, color="black")
        ax.bar(churn_labels, avg_tput_gbps)

    for i in range(len(axs.flat)):
        ax = axs.flat[i]

        if i >= len(all_s):
            fig.delaxes(ax)
            continue

        ax.set_ylim(ymin=0, ymax=3000)

        ax.set_ylabel("Throughput (bps)")
        ax.set_xlabel("Churn (fpm)")

        ax.set_yticks([600, 1200, 1800, 2400, 3000], labels=["600G", "1.2T", "1.8T", "2.4T", "3T"])
        ax.yaxis.set_minor_locator(MultipleLocator(300))

    # Hide x labels and tick labels for top plots and y ticks for right plots.
    for ax in axs.flat:
        ax.label_outer()

    # fig.set_size_inches(width * 0.4, height * 3)
    # fig.set_figwidth(width * 0.6)
    fig.tight_layout(pad=0.1)

    fig_file_pdf = Path(file)
    print("-> ", fig_file_pdf)
    plt.savefig(str(fig_file_pdf))


def plot_pps(data: HeatmapData, file: Path):
    avg_data = data.get_avg_values()
    keys = avg_data.keys()
    all_s = sorted(set([key.s for key in keys]))
    all_churn = sorted(set([key.churn_fpm for key in keys]))
    churn_labels = [whole_number_to_label(churn) for churn in all_churn]
    fig, axs = plt.subplots(math.ceil(len(all_s) / 2), 2)

    for i in range(len(all_s)):
        ax = axs[int(i / 2), i % 2]
        s = all_s[i]

        ax.set_title(f"Zipf parameter: {s:.2f}")

        churn_labels = [whole_number_to_label(churn) for churn in all_churn]
        avg_tput_mpps = [avg_data[Key(s, churn)].dut_egress_pps / 1e6 for churn in all_churn]
        stdev_tput_mpps = [data.get_stdev_values()[Key(s, churn)].dut_egress_pps / 1e6 for churn in all_churn]

        ax.errorbar(churn_labels, avg_tput_mpps, yerr=stdev_tput_mpps, fmt="none", capsize=capsize, markeredgewidth=markeredgewidth, elinewidth=elinewidth, color="black")
        ax.bar(churn_labels, avg_tput_mpps)

    for i in range(len(axs.flat)):
        ax = axs.flat[i]

        if i >= len(all_s):
            fig.delaxes(ax)
            continue

        ax.set_ylim(ymin=0, ymax=3500)

        ax.set_ylabel("Throughput (pps)")
        ax.set_xlabel("Churn (fpm)")

        ax.set_yticks([500, 1000, 1500, 2000, 2500, 3000, 3500], labels=["500M", "1G", "1.5G", "2G", "2.5G", "3G", "3.5G"])
        ax.yaxis.set_minor_locator(MultipleLocator(250))

    # Hide x labels and tick labels for top plots and y ticks for right plots.
    for ax in axs.flat:
        ax.label_outer()

    # fig.set_size_inches(width * 0.4, height * 3)
    # fig.set_figwidth(width * 0.6)
    fig.tight_layout(pad=0.1)

    fig_file_pdf = Path(file)
    print("-> ", fig_file_pdf)
    plt.savefig(str(fig_file_pdf))


def discrete(data, ax):
    ax.grid(False)
    ax.spines[:].set_visible(False)
    ax.set_xticks(np.arange(data.shape[1] + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(data.shape[0] + 1) - 0.5, minor=True)
    ax.grid(which="minor", color="w", linestyle="-", linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)


def plot_heatmap(data: HeatmapData, file: Path, cmap="Blues", show_errors: bool = True):
    avg_data = data.get_avg_values()
    keys = avg_data.keys()
    all_s = sorted(set([key.s for key in keys]))
    all_churn = sorted(set([key.churn_fpm for key in keys]), reverse=True)

    matrix = np.zeros((len(all_churn), len(all_s)))
    for key in keys:
        i = all_churn.index(key.churn_fpm)
        j = all_s.index(key.s)
        matrix[i, j] = avg_data[key].dut_egress_pps / 1e6

    s_labels = [f"{s:.1f}" for s in all_s]
    churn_labels = [f"{whole_number_to_label(c)}" for c in all_churn]

    # Nice colormaps:
    # https://matplotlib.org/stable/tutorials/colors/colormaps.html
    # - plasma
    # - viridis
    # - rainbow
    # - Blues
    # - Reds

    fig, ax = plt.subplots(constrained_layout=True)
    ax.imshow(matrix, vmin=0, vmax=TPUT_MPPS_MAX, cmap=cmap, aspect="auto")

    # Show all ticks and label them with the respective list entries
    ax.set_xticks(range(len(all_s)), labels=s_labels)
    ax.set_yticks(range(len(all_churn)), labels=churn_labels)

    ax.set_xlabel("Skew (Zipf parameter)")
    ax.set_ylabel("Churn (fpm)")

    # Rotate the tick labels and set their alignment.
    # plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    ax.grid(False)

    ax.spines[:].set_visible(False)
    ax.set_xticks(np.arange(matrix.shape[1] + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(matrix.shape[0] + 1) - 0.5, minor=True)
    ax.tick_params(which="minor", bottom=False, left=False)
    ax.tick_params(axis="both", length=0)

    for key in keys:
        i = all_churn.index(key.churn_fpm)
        j = all_s.index(key.s)
        pps = int(avg_data[key].dut_egress_pps)
        err = int(data.get_stdev_values()[key].dut_egress_pps)

        avg_label = int(pps / 1e6)
        err_label = int(err / 1e6)

        if avg_data[key].label is not None:
            label = avg_data[key].label
            assert label is not None
        else:
            if avg_label == 0:
                label = "$<1$\nMpps"
            else:
                label = f"{avg_label}±{err_label}\nMpps" if show_errors else f"{avg_label}\nMpps"

        color = "black" if pps < TPUT_MPPS_MAX * 1e6 / 2 else "white"

        text = ax.text(j, i, label, ha="center", va="center", color=color)
        if avg_data[key].label is not None:
            text.set_fontsize(5)
        else:
            text.set_fontsize(doc.scriptsize)
        text.set_fontweight("bold")

    fig.set_size_inches(width, height * 1.4)
    # fig.tight_layout(pad=0.1)

    print("-> ", file)
    plt.savefig(str(file), bbox_inches="tight", pad_inches=0)


def plot_heatmap_estimation(data: HeatmapData, file: Path, show_errors: bool = True):
    plot_heatmap(data, file, cmap="Oranges", show_errors=show_errors)


def plot_heatmap_data_structures(data: HeatmapData, file: Path, cmap="Blues", show_errors: bool = True):
    avg_data = data.get_avg_values()
    keys = avg_data.keys()
    all_s = sorted(set([key.s for key in keys]))
    all_churn = sorted(set([key.churn_fpm for key in keys]), reverse=True)

    matrix = np.zeros((len(all_churn), len(all_s)))
    for key in keys:
        i = all_churn.index(key.churn_fpm)
        j = all_s.index(key.s)
        matrix[i, j] = avg_data[key].dut_egress_pps / 1e6

    s_labels = [f"{s:.2f}" for s in all_s]
    churn_labels = [f"{whole_number_to_label(c)}" for c in all_churn]

    # Nice colormaps:
    # https://matplotlib.org/stable/tutorials/colors/colormaps.html
    # - plasma
    # - viridis
    # - rainbow
    # - Blues
    # - Reds

    fig, ax = plt.subplots(constrained_layout=True)
    ax.imshow(matrix, vmin=0, vmax=TPUT_MPPS_MAX, cmap=cmap, aspect="auto")

    # Show all ticks and label them with the respective list entries
    ax.set_xticks(range(len(all_s)), labels=s_labels)
    ax.set_yticks(range(len(all_churn)), labels=churn_labels)

    ax.set_xlabel("Skew (Zipf parameter)")
    ax.set_ylabel("Churn (fpm)")

    # Rotate the tick labels and set their alignment.
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

    ax.grid(False)

    ax.spines[:].set_visible(False)
    ax.set_xticks(np.arange(matrix.shape[1] + 1) - 0.5, minor=True)
    ax.set_yticks(np.arange(matrix.shape[0] + 1) - 0.5, minor=True)
    ax.tick_params(which="minor", bottom=False, left=False)

    for key in keys:
        i = all_churn.index(key.churn_fpm)
        j = all_s.index(key.s)
        pps = int(avg_data[key].dut_egress_pps)
        err = int(data.get_stdev_values()[key].dut_egress_pps)

        avg_label = int(pps / 1e6)
        err_label = int(err / 1e6)

        label = f"{avg_label}±{err_label}\nMpps" if show_errors else f"{avg_label}\nMpps"

        color = "black" if pps < TPUT_MPPS_MAX * 1e6 / 2 else "white"

        text = ax.text(j, i, label, ha="center", va="center", color=color)
        text.set_fontsize(6)
        text.set_fontweight("bold")

    fig.set_size_inches(width, height * 0.8)
    # fig.tight_layout(pad=0.1)

    print("-> ", file)
    plt.savefig(str(file))


def plot_bps_scatter(data: HeatmapData, file: Path):
    raw_data = data.get_raw()
    avg_data = data.get_avg_values()
    keys = data.get_keys()
    all_s = sorted(set([key.s for key in keys]))
    all_churn = sorted(set([key.churn_fpm for key in keys]))
    churn_labels = [whole_number_to_label(churn) for churn in all_churn]
    fig, axs = plt.subplots(len(all_s))

    x_span = 0.5

    for i in range(len(all_s)):
        ax = axs[i]
        s = all_s[i]

        for j in range(len(all_churn)):
            churn = all_churn[j]
            key = Key(s, churn)
            values = [v.dut_egress_bps / 1e9 for v in raw_data[key]]
            avg_value = avg_data[key].dut_egress_bps / 1e9

            total_values = len(values)
            dx = x_span / (total_values + 1)

            xs = [j - (x_span / 2) + dx * k for k in range(1, total_values + 1)]
            ys = values

            ax.bar(j, avg_value, alpha=0.2, color="black", width=x_span, align="center", edgecolor="black")

            colors = iter(colormaps["Dark2"](np.linspace(0, 1, len(xs))))

            ax.set_title(f"Zipf parameter: {s:.2f}")
            for x, y in zip(xs, ys):
                ax.scatter(x, y, s=15, color=next(colors))

    for i in range(len(axs.flat)):
        ax = axs.flat[i]

        if i >= len(all_s):
            fig.delaxes(ax)
            continue

        ax.set_ylim(ymin=0, ymax=3000)

        ax.set_xlabel("Churn (fpm)")
        ax.set_ylabel("Throughput (bps)")

        ax.set_xticks(range(len(all_churn)), labels=churn_labels)
        ax.set_yticks([600, 1200, 1800, 2400, 3000], labels=["600G", "1.2T", "1.8T", "2.4T", "3T"])

        ax.yaxis.set_minor_locator(MultipleLocator(300))

    # Hide x labels and tick labels for top plots and y ticks for right plots.
    for ax in axs.flat:
        ax.label_outer()

    fig.set_size_inches(width, height * 0.8)
    # fig.set_figwidth(width * 1)
    fig.tight_layout(pad=0.1)

    fig_file_pdf = Path(file)
    print("-> ", fig_file_pdf)
    plt.savefig(str(fig_file_pdf))
