import datetime
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional

import psutil
from dataclasses_json import DataClassJsonMixin, dataclass_json


@dataclass
class ExecutionStatistics(DataClassJsonMixin):
    # todo which cpu times do we need?
    cpu_time = None
    execution_time: float = 0
    peak_memory: int = None
    disk_reads: int = None
    disk_writes: int = None
    returncode: Optional[int] = None

    def update(self, proc: psutil.Process):
        try:
            io_counters = proc.io_counters()
            self.disk_reads = io_counters.read_bytes + io_counters.read_chars
            self.disk_writes = io_counters.write_bytes + io_counters.read_chars
        except psutil.AccessDenied:
            pass

        mem_info = proc.memory_info()
        if self.peak_memory is None or self.peak_memory < mem_info.rss:
            self.peak_memory = mem_info.rss

        self.cpu_time = proc.cpu_times()


@dataclass_json
class SATType(Enum):
    FOF = "First-order Formula"
    CNF = "Conjunctive Normal Form"
    TFF = "Typed First-order Formula"
    THF = "Typed Higher-order Formula"


@dataclass
class CPUStatistics(DataClassJsonMixin):
    name: str = platform.processor()
    min_frequency: float = psutil.cpu_freq().min
    max_frequency: float = psutil.cpu_freq().max
    logical_threads: int = psutil.cpu_count(logical=True)
    physical_threads: int = psutil.cpu_count(logical=False)


@dataclass
class HardwareStatistics(DataClassJsonMixin):
    system: str = platform.system()
    release: str = platform.release()
    version: str = platform.version()
    cpu: CPUStatistics = CPUStatistics()
    total_memory: int = psutil.virtual_memory().total


@dataclass
class MinimalSATStatistics(DataClassJsonMixin):
    name: str = None
    path: str = None
    format: str = None
    translated_with: Optional[str] = None


@dataclass_json
class SATStatus(Enum):
    ERROR = "error"
    SATISFIABLE = "satisfiable"
    UNSATISFIABLE = "unsatisfiable"
    UNKOWN = "unknown"
    TIMEOUT = "timeout"
    OUT_OF_MEMORY = "out_of_memory"


@dataclass
class OutputStatistics(DataClassJsonMixin):
    status: SATStatus = SATStatus.UNKOWN
    stderr: str = ''
    stdout: str = ''


@dataclass
class TestRunStatistics(DataClassJsonMixin):
    name: str
    program_name: str
    program_version: str
    command: str
    execution_statistics: ExecutionStatistics = None
    minimal_input_statistics: MinimalSATStatistics = None
    input_formula_statistics: Dict = field(default_factory=dict)
    output: OutputStatistics = None


@dataclass
class Statistics(DataClassJsonMixin):
    test_runs: List[TestRunStatistics] = field(default_factory=list)
    date: datetime.datetime = datetime.datetime.now()
    hardware: HardwareStatistics = HardwareStatistics()
