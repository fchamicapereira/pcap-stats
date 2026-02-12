#!/usr/bin/env python3

import os
import time
import humanize
import asyncio
import rich
import graphviz
import signal

from argparse import ArgumentParser
from asyncio.subprocess import PIPE, STDOUT
from datetime import timedelta
from pathlib import Path
from typing import Optional

SPAWN_COLOR = "cyan"
DONE_COLOR = "green"
SKIP_COLOR = "yellow"
ERROR_COLOR = "red"
DEBUG_COLOR = "white"
ABORT_COLOR = "magenta"

NOW = time.strftime("%Y%m%d-%H%M%S")

CURRENT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
PROJECT_DIR = (CURRENT_DIR / "..").resolve()
REPORTS_DIR = PROJECT_DIR / "reports"
PLOTS_DIR = PROJECT_DIR / "plots"
PLOT_SCRIPTS_DIR = PROJECT_DIR / "tools"

PCAP_STATS_TRACKER_BIN = PROJECT_DIR / "build" / "bin" / "pcap-stats"

DEFAULT_EPOCH_DURATION_NS = 1_000_000_000  # 1 second


class Task:
    def __init__(
        self,
        name: str,
        cmd: str,
        env_vars: dict[str, str] = {},
        cwd: Optional[Path] = None,
        # Relations with other tasks
        next: list["Task"] = [],
        # File dependencies
        files_consumed: list[Path] | list[str] = [],
        files_produced: list[Path] | list[str] = [],
        # Execution options
        skip_execution: bool = False,
        ignore_skip_if_already_produced: bool = False,
        # Metadata
        show_cmds_output: bool = False,
        show_cmds: bool = False,
        silence: bool = False,
    ):
        self.id = "_".join(name.split(" "))
        self.name = name
        self.cmd = cmd
        self.env_vars = env_vars
        self.cwd = cwd

        self.prev = set()
        self.next = set(next)

        self.files_consumed = set([Path(f) for f in files_consumed])
        self.files_produced = set([Path(f) for f in files_produced])

        self.skip_execution = skip_execution
        self.ignore_skip_if_already_produced = ignore_skip_if_already_produced

        self.show_cmds_output = show_cmds_output
        self.show_cmds = show_cmds
        self.silence = silence

        self.done = False

        for next_task in self.next:
            next_task.prev.add(self)

    def __eq__(self, other: "Task"):
        if not isinstance(other, Task):
            return False
        if self.id != other.id:
            return False
        if self.cmd != other.cmd:
            return False
        if self.cwd != other.cwd:
            return False
        if self.env_vars != other.env_vars:
            return False
        return True

    def __hash__(self):
        return hash((self.name, self.cmd, frozenset(self.env_vars.items()), self.cwd))

    def __repr__(self):
        return f"Task(id={self.id})"

    def log(self, msg: str, color: Optional[str] = None):
        if self.silence and color != ERROR_COLOR:
            return

        prefix = ""
        suffix = ""
        if color:
            prefix = f"[{color}]"
            suffix = f"[/{color}]"

        rich.print(f"{prefix}\\[{self.name}] {msg}{suffix}", flush=True)

    def log_failed_cmd(self, retcode: int):
        filename = f"failed-cmds-{NOW}.txt"
        with open(filename, "a") as f:
            f.write(f"retcode={retcode},cmd={self.cmd}\n")

    def is_ready(self) -> bool:
        for prev_task in self.prev:
            if not prev_task.done:
                return False
        return True

    def _start(self):
        self.start_time = time.perf_counter()

    def _end(self):
        self.done = True
        self.end_time = time.perf_counter()
        self.elapsed_time = self.end_time - self.start_time

    async def _run(
        self,
        skip_if_already_produced: bool = True,
    ) -> bool:
        if self.done:
            self.log("already executed, skipping", color=SKIP_COLOR)
            return True

        if self.show_cmds and not self.silence:
            flattened_env_vars = " ".join([f"{k}={v}" for k, v in self.env_vars.items()])
            print(f"[{self.name}] {flattened_env_vars} {self.cmd}")

        if self.skip_execution:
            self.log("skipping execution", color=SKIP_COLOR)
            return True

        for file in self.files_consumed:
            if not file.exists():
                self.log(f"consumed file '{file}' does not exist, skipping execution", color=ERROR_COLOR)
                return True

        all_files_produced = len(self.files_produced) > 0 and all([file.exists() for file in self.files_produced])
        if not self.ignore_skip_if_already_produced and all_files_produced and skip_if_already_produced:
            self.log("all product files already exist, skipping execution", color=SKIP_COLOR)
            return True

        self.log("spawning", color=SPAWN_COLOR)

        try:
            process = await asyncio.create_subprocess_exec(
                *self.cmd.split(" "),
                stdout=PIPE,
                stderr=STDOUT,
                bufsize=0,
                cwd=self.cwd,
                env={**self.env_vars, **dict(list(os.environ.items()))},
            )

            assert process, "Process creation failed"

            stdout_data, _ = await process.communicate()
            stdout = stdout_data.decode().strip() if stdout_data else ""

            assert process.returncode is not None, "Process return code is None"

            if process.returncode < 0:
                self.log(f"terminated by signal {-process.returncode}", color=ABORT_COLOR)
                if process.returncode not in [-signal.SIGINT]:
                    self.log_failed_cmd(process.returncode)
                return False

            if process.returncode != 0 or self.show_cmds_output:
                if process.returncode != 0:
                    self.log(f"failed with return code {process.returncode}", color=ERROR_COLOR)
                    self.log("command:", color=ERROR_COLOR)
                    print(self.cmd)
                    self.log("output:", color=ERROR_COLOR)
                    print(stdout)
                    self.log_failed_cmd(process.returncode)
                    return False
                elif not self.silence:
                    print(stdout)
        except asyncio.CancelledError:
            self.log("task was cancelled", color=ERROR_COLOR)
            return False
        except Exception as e:
            self.log(f"error while executing command: {e}", color=ERROR_COLOR)
            return False

        return True

    async def run(
        self,
        skip_if_already_produced: bool = True,
    ) -> bool:
        self._start()
        success = await self._run(skip_if_already_produced)
        self._end()

        if success:
            missing_product_files = [f for f in self.files_produced if not f.exists()]
            if missing_product_files:
                self.log(f"some produced files are missing: {', '.join(str(f) for f in missing_product_files)}", color=ERROR_COLOR)
                success = False
            else:
                delta = timedelta(seconds=self.elapsed_time)
                self.log(f"done ({humanize.precisedelta(delta, minimum_unit='milliseconds')})", color=DONE_COLOR)

        return success

    def dump_execution_plan(self, indent: int = 0):
        rich.print("  " * indent + f"{self}")
        for next_task in self.next:
            next_task.dump_execution_plan(indent + 1)


class Orchestrator:
    def __init__(self, tasks: list[Task] = []):
        self.initial_tasks: set[Task] = set()
        self.files_to_producers: dict[Path, Task] = {}
        self.total_elapsed_time: timedelta = timedelta(0)

        pending_tasks = set(tasks)
        while pending_tasks:
            task = pending_tasks.pop()
            self.add_task(task)
            pending_tasks.update(task.next)

    def add_task(self, task: Task):
        for file in task.files_produced:
            if file in self.files_to_producers:
                assert self.files_to_producers[file] == task, f"File {file} is already produced by another task: {self.files_to_producers[file].name}"
            self.files_to_producers[file] = task

        for file in task.files_consumed:
            if file in self.files_to_producers:
                task.prev.add(self.files_to_producers[file])
                self.files_to_producers[file].next.add(task)

        if len(task.prev) == 0:
            self.initial_tasks.add(task)

    def get_all_tasks(self) -> set[Task]:
        all_tasks = set()

        next_tasks = set(self.initial_tasks)
        while next_tasks:
            task = next_tasks.pop()
            all_tasks.add(task)
            next_tasks.update(task.next)

        return all_tasks

    def size(self) -> int:
        return len(self.get_all_tasks())

    def visualize(self, dot_file: Optional[str | Path] = None):
        dot = graphviz.Digraph(comment="Execution Plan", format="pdf")
        initial_graph = graphviz.Digraph(name="cluster_0", comment="Initial Tasks")
        final_graph = graphviz.Digraph(name="cluster_1", comment="Final Tasks")

        dot.attr(kw="graph", rankdir="LR")
        dot.attr(kw="node", style="filled", shape="box")
        initial_graph.attr(label="Initial Tasks")
        final_graph.attr(label="Final Tasks")

        assert initial_graph, "Failed to create subgraph for initial tasks"

        all_tasks = self.get_all_tasks()

        for task in all_tasks:
            color = SPAWN_COLOR if not task.skip_execution else SKIP_COLOR

            if task in self.initial_tasks:
                initial_graph.node(task.id, label=task.name, fillcolor=color)
            elif len(task.next) == 0:
                final_graph.node(task.id, label=task.name, fillcolor=color)
            else:
                dot.node(task.id, label=task.name, fillcolor=color)

        dot.subgraph(initial_graph)
        dot.subgraph(final_graph)

        for task in all_tasks:
            for next_task in task.next:
                dot.edge(task.id, next_task.id)

        if not dot_file:
            dot_file = Path("/tmp") / f"execution_plan_{int(time.time())}.dot"
            print(f"Saving execution plan to {dot_file}")

        dot.render(dot_file)

    async def _worker(
        self,
        queue: asyncio.LifoQueue,
        skip_if_already_produced: bool,
    ):
        task: Optional[Task] = None

        while True:
            try:
                task = await queue.get()
                if task is None:
                    break

                assert isinstance(task, Task), f"Expected Task instance, got {type(task)}"

                start = time.perf_counter()
                success = await task.run(skip_if_already_produced)
                end = time.perf_counter()
                delta = timedelta(seconds=end - start)
                self.total_elapsed_time += delta

                if success:
                    for next_task in task.next:
                        if next_task.is_ready():
                            await queue.put(next_task)
            except Exception as e:
                rich.print(f"[{ERROR_COLOR}]Error in worker: {e}[/{ERROR_COLOR}]")
                pass
            finally:
                queue.task_done()

    async def _run(
        self,
        skip_if_already_produced: bool,
        max_concurrent_tasks: int = -1,
    ):
        queue = asyncio.LifoQueue()
        loop = asyncio.get_running_loop()
        shutdown_event = asyncio.Event()

        if max_concurrent_tasks <= 0:
            max_concurrent_tasks = os.cpu_count() or 8

        def handle_sigint():
            shutdown_event.set()

        if hasattr(signal, "SIGINT"):
            loop.add_signal_handler(signal.SIGINT, handle_sigint)
        if hasattr(signal, "SIGTERM"):
            loop.add_signal_handler(signal.SIGTERM, handle_sigint)

        for task in self.initial_tasks:
            await queue.put(task)

        async_tasks = []
        for _ in range(max_concurrent_tasks):
            task = asyncio.create_task(self._worker(queue, skip_if_already_produced))
            async_tasks.append(task)

        await queue.join()

        for task in async_tasks:
            task.cancel()

        await asyncio.gather(*async_tasks, return_exceptions=True)

    def run(
        self,
        skip_if_already_produced: bool = True,
        max_concurrent_tasks: int = -1,
    ):
        start = time.perf_counter()
        asyncio.run(self._run(skip_if_already_produced, max_concurrent_tasks))
        end = time.perf_counter()

        delta = timedelta(seconds=end - start)

        rich.print(f"[{DONE_COLOR}]Execution time:   {humanize.precisedelta(delta, minimum_unit='milliseconds')}[/{DONE_COLOR}]")
        rich.print(f"[{DONE_COLOR}]Total tasks time: {humanize.precisedelta(self.total_elapsed_time, minimum_unit='milliseconds')}[/{DONE_COLOR}]")

    def dump_execution_plan(self):
        for task in self.initial_tasks:
            task.dump_execution_plan()


def build_pcap_stats_tracker(
    debug: bool,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    cmd = "./build-debug.sh" if debug else "./build.sh"

    files_consumed = []
    files_produced = [PCAP_STATS_TRACKER_BIN]

    return Task(
        "build_pcap_stats_tracker",
        cmd,
        cwd=PROJECT_DIR,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        silence=silence,
    )


def run_pcap_stats_tracker(
    pcap: Path,
    epoch_duration_ns: int,
    force: bool = False,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    out_report = REPORTS_DIR / f"{pcap.stem}.json"

    files_consumed = [PCAP_STATS_TRACKER_BIN, pcap]
    files_produced = [out_report]

    cmd = f"{PCAP_STATS_TRACKER_BIN} {pcap} --out {out_report} --epoch {epoch_duration_ns}"

    return Task(
        f"run_pcap_stats_tracker_{pcap.stem}",
        cmd,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        ignore_skip_if_already_produced=force,
        silence=silence,
    )


def plot_flow_dts_us_cdf(
    pcap: Path,
    force_replot: bool,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    report = REPORTS_DIR / f"{pcap.stem}.json"

    files_consumed = [report]
    files_produced = [PLOTS_DIR / f"{pcap.stem}_flow_ipt_cdf.pdf"]

    cmd = f"./plot_flow_dts_us_cdf.py {report}"

    return Task(
        f"run_plot_flow_dts_us_cdf_{pcap.stem}",
        cmd,
        cwd=PLOT_SCRIPTS_DIR,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        ignore_skip_if_already_produced=force_replot,
        silence=silence,
    )


def plot_flow_duration_us_cdf(
    pcap: Path,
    force_replot: bool,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    report = REPORTS_DIR / f"{pcap.stem}.json"

    files_consumed = [report]
    files_produced = [PLOTS_DIR / f"{pcap.stem}_fct_cdf.pdf"]

    cmd = f"./plot_flow_duration_us_cdf.py {report}"

    return Task(
        f"run_plot_flow_duration_us_cdf_{pcap.stem}",
        cmd,
        cwd=PLOT_SCRIPTS_DIR,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        ignore_skip_if_already_produced=force_replot,
        silence=silence,
    )


def plot_pkt_bytes_cdf(
    pcap: Path,
    force_replot: bool,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    report = REPORTS_DIR / f"{pcap.stem}.json"

    files_consumed = [report]
    files_produced = [PLOTS_DIR / f"{pcap.stem}_pkt_bytes_cdf.pdf"]

    cmd = f"./plot_pkt_bytes_cdf.py {report}"

    return Task(
        f"run_plot_pkt_bytes_cdf_{pcap.stem}",
        cmd,
        cwd=PLOT_SCRIPTS_DIR,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        ignore_skip_if_already_produced=force_replot,
        silence=silence,
    )


def plot_pkts_per_flow_cdf(
    pcap: Path,
    force_replot: bool,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    report = REPORTS_DIR / f"{pcap.stem}.json"

    files_consumed = [report]
    files_produced = [PLOTS_DIR / f"{pcap.stem}_pkts_per_flow_cdf.pdf"]

    cmd = f"./plot_pkts_per_flow_cdf.py {report}"

    return Task(
        f"run_plot_pkts_per_flow_cdf_{pcap.stem}",
        cmd,
        cwd=PLOT_SCRIPTS_DIR,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        ignore_skip_if_already_produced=force_replot,
        silence=silence,
    )


def plot_top_k_flows_bytes_cdf(
    pcap: Path,
    force_replot: bool,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    report = REPORTS_DIR / f"{pcap.stem}.json"

    files_consumed = [report]
    files_produced = [PLOTS_DIR / f"{pcap.stem}_top_k_flows_bytes_cdf.pdf"]

    cmd = f"./plot_top_k_flows_bytes_cdf.py {report}"

    return Task(
        f"run_plot_top_k_flows_bytes_cdf_{pcap.stem}",
        cmd,
        cwd=PLOT_SCRIPTS_DIR,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        ignore_skip_if_already_produced=force_replot,
        silence=silence,
    )


def plot_top_k_flows_cdf(
    pcap: Path,
    force_replot: bool,
    skip_execution: bool = False,
    show_cmds_output: bool = False,
    show_cmds: bool = False,
    silence: bool = False,
) -> Task:
    report = REPORTS_DIR / f"{pcap.stem}.json"

    files_consumed = [report]
    files_produced = [PLOTS_DIR / f"{pcap.stem}_top_k_flows_cdf.pdf"]

    cmd = f"./plot_top_k_flows_cdf.py {report}"

    return Task(
        f"run_plot_top_k_flows_cdf_{pcap.stem}",
        cmd,
        cwd=PLOT_SCRIPTS_DIR,
        files_consumed=files_consumed,
        files_produced=files_produced,
        skip_execution=skip_execution,
        show_cmds_output=show_cmds_output,
        show_cmds=show_cmds,
        ignore_skip_if_already_produced=force_replot,
        silence=silence,
    )


if __name__ == "__main__":
    parser = ArgumentParser(description="Orchestrator for executing tasks with dependencies")

    parser.add_argument("pcaps", nargs="+", type=Path, help="Paths to PCAP files to process")
    parser.add_argument("--epoch", type=int, default=DEFAULT_EPOCH_DURATION_NS, help="Epoch duration in nanoseconds for the pcap stats tracker")

    parser.add_argument("--force", action="store_true", help="Force execution of all tasks, even if their output files already exist")
    parser.add_argument("--force-replot", action="store_true", help="Force re-plotting even if the output files already exist")
    parser.add_argument("--force-report", action="store_true", help="Force report generation even if the output files already exist")

    parser.add_argument("--debug", action="store_true", default=False, help="Enable debug mode (synapse runs much slower)")
    parser.add_argument("--show-cmds-output", action="store_true", default=False, help="Show command output during execution")
    parser.add_argument("--show-cmds", action="store_true", default=False, help="Show requested commands during execution")
    parser.add_argument("--show-execution-plan", action="store_true", default=False, help="Show execution plan")
    parser.add_argument("--dry-run", action="store_true", default=False)
    parser.add_argument("--silence", action="store_true", help="Don't show any output from the commands being executed, except for errors")

    args = parser.parse_args()

    Path.mkdir(REPORTS_DIR, exist_ok=True)
    Path.mkdir(PLOTS_DIR, exist_ok=True)

    orchestrator = Orchestrator()

    orchestrator.add_task(
        build_pcap_stats_tracker(
            debug=args.debug,
            skip_execution=args.dry_run,
            show_cmds_output=args.show_cmds_output,
            show_cmds=args.show_cmds,
            silence=args.silence,
        )
    )

    for pcap in args.pcaps:
        orchestrator.add_task(
            run_pcap_stats_tracker(
                pcap=pcap,
                epoch_duration_ns=args.epoch,
                force=args.force_report or args.force,
                skip_execution=args.dry_run,
                show_cmds_output=args.show_cmds_output,
                show_cmds=args.show_cmds,
                silence=args.silence,
            )
        )

        plotter_tasks = [
            plot_flow_dts_us_cdf,
            plot_flow_duration_us_cdf,
            plot_pkt_bytes_cdf,
            plot_pkts_per_flow_cdf,
            plot_top_k_flows_bytes_cdf,
            plot_top_k_flows_cdf,
        ]

        for plotter_task in plotter_tasks:
            orchestrator.add_task(
                plotter_task(
                    pcap=pcap,
                    force_replot=args.force_replot or args.force,
                    skip_execution=args.dry_run,
                    show_cmds_output=args.show_cmds_output,
                    show_cmds=args.show_cmds,
                    silence=args.silence,
                )
            )

    if args.show_execution_plan:
        orchestrator.visualize()

    orchestrator.run(
        skip_if_already_produced=not args.force,
    )
