import datetime
import platform
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List

import psutil as psutil

from src import logger


@dataclass
class ExecutionStatistics:
    # todo which cpu times do we need?
    cpu_time = None
    execution_time: float = 0
    peak_memory: int = None
    disk_reads: int = None
    disk_writes: int = None
    _update_io = True

    def disable_io(self):
        self._update_io = False

    def update(self, proc: psutil.Process):
        if self._update_io:
            io_counters = proc.io_counters()
            self.disk_reads = io_counters.read_bytes + io_counters.read_chars
            self.disk_writes = io_counters.write_bytes + io_counters.read_chars

        mem_info = proc.memory_info()
        if self.peak_memory is None or self.peak_memory < mem_info.rss:
            self.peak_memory = mem_info.rss

        self.cpu_time = proc.cpu_times()


class MonitoredProcess(subprocess.Popen):

    def __init__(self, *args, **kwargs):
        self.exec_stats = ExecutionStatistics()
        try:
            psutil.Process().io_counters()
        except psutil.AccessDenied:
            logger.warning("Can not disk IO info - permission denied")
            self.exec_stats.disable_io()

        super().__init__(*args, **kwargs)
        self._start = time.time()
        self.proc = psutil.Process(self.pid)
        self.poll()

    def poll(self):
        if super().poll() is not None:
            return super().poll()

        # can not do it in __exit__, because process no longer not exists there
        self.exec_stats.update(self.proc)

        return None

    def stop(self):
        self.__exit__(None, None, None)

    def get_statistics(self) -> ExecutionStatistics:
        return self.exec_stats

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exec_stats.execution_time = time.time() - self._start


class SATType(Enum):
    FOF = "First-order Formula"
    CNF = "Conjunctive Normal Form"
    TFF = "Typed First-order Formula"
    THF = "Typed Higher-order Formula"


@dataclass
class CPUStatistics:
    name: str = platform.processor()
    min_frequency: float = psutil.cpu_freq().min
    max_frequency: float = psutil.cpu_freq().max
    logical_threads: int = psutil.cpu_count(logical=True)
    physical_threads: int = psutil.cpu_count(logical=False)


@dataclass
class HardwareStatistics:
    system: str = platform.system()
    release: str = platform.release()
    version: str = platform.version()
    cpu: CPUStatistics = CPUStatistics()
    total_memory: int = psutil.virtual_memory().total


@dataclass
class SATStatistics:
    name: str = None
    path: str = None
    # list of commands used to translate
    translated_with: List[List[str]] = field(default_factory=list)
    SAT_type: SATType = None
    format: str = None
    number_of_clauses: int = None
    number_of_atoms: int = None
    maximal_clause_size: int = None
    number_of_predicates: int = None
    number_of_functors: int = None
    number_of_variables: int = None
    maximal_term_depth: int = None


@dataclass
class SATStatus:
    ERROR = "error"
    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"
    UNKOWN = "UNKNOWN"


@dataclass
class OutputStatistics:
    returncode: int = None
    status: SATStatus = None
    error: str = None
    output: str = None


@dataclass
class TestCaseStatistics:
    name: str
    command: List[str]
    execution_statistics: ExecutionStatistics = None
    input: SATStatistics = None
    output: OutputStatistics = None


@dataclass
class TestSuiteStatistics:
    program_name: str
    program_version: str
    test_cases: List[TestCaseStatistics] = field(default_factory=list)


@dataclass
class Statistics:
    test_suites: List[TestSuiteStatistics] = field(default_factory=list)
    date: datetime.datetime = datetime.datetime.now()
    hardware: HardwareStatistics = HardwareStatistics()


if __name__ == '__main__':
    import functools

    proc = functools.partial(MonitoredProcess, ['sleep', '5'])
    with proc() as running_process:
        while running_process.poll():
            time.sleep(0.1)

    print(running_process.get_statistics())