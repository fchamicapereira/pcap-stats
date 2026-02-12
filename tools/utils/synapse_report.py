from pathlib import Path

from msgspec.json import Decoder
from msgspec import Struct


class HeuristicMeta(Struct):
    name: str
    description: str


class Heuristic(Struct):
    meta: list[HeuristicMeta]
    score: list[int]


class Implementation(Struct):
    addr: int
    implementation: str


class AvgChildrenPerNode(Struct):
    avg: float
    node_id: int


class SearchMeta(Struct):
    avg_bdd_size: int
    avg_children_per_node: list[AvgChildrenPerNode]
    backtracks: int
    branching_factor: float
    elapsed_time_seconds: int
    finished_eps: int
    ss_size: int
    steps: int
    total_ss_size_estimation: float
    unfinished_eps: int


class SynapseReport(Struct):
    bdd: str
    heuristic: Heuristic
    implementations: list[Implementation]
    name: str
    profile_file: str
    search_meta: SearchMeta
    seed: int
    targets_config_file: str
    tput_estimation_pps: int
    tput_estimation_bps: int


def parse_synapse_report(file: Path) -> SynapseReport:
    decoder = Decoder(SynapseReport)
    with open(file, "rb") as f:
        json_bytes = f.read()
        data = decoder.decode(json_bytes)
        return data
