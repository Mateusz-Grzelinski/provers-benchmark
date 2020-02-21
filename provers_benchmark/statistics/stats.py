import datetime
import platform
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Union, Optional

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
    # list of commands used to translate
    translated_with: Optional[str] = None


@dataclass
class ConjunctiveNormalFormFirstOrderLogicSATStatistics(DataClassJsonMixin):
    SAT_type: SATType = None
    # number_of_clauses: int = None
    # number_of_unit_clauses: int = None
    # number_of_atoms: int = None
    # maximal_clause_size: int = None
    # average_clause_size: int = None
    # number_of_predicates: int = None
    # predicate_arities: str = None
    # number_of_functors: int = None
    # number_of_constant_functors: int = None
    # functor_arities: str = None
    # number_of_variables: int = None
    # number_of_singleton_variables: int = None
    # maximal_term_depth: int = None
    # total_number_of_literals: int = None
    # number_of_literals: int = None
    # total_number_of_functors: int = None
    # total_number_of_variables: int = None


@dataclass
class ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo(DataClassJsonMixin):
    number_of_variables: int = 0
    number_of_clauses: int = 0
    max_clause_size: int = 0
    clause_sizes: Dict[int, int] = field(default_factory=dict)
    """Dict[clause_size, number_of_cluases]"""
    number_of_variables_with_always_connectives: int = 0
    number_of_variables_with_eventually_connectives: int = 0
    number_of_variables_without_connective: int = 0
    number_of_negated_variables: int = 0


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
    command: List[str]
    execution_statistics: ExecutionStatistics = None
    minimal_input_statistics: MinimalSATStatistics = None
    input_statistics: Union[ConjunctiveNormalFormFirstOrderLogicSATStatistics,
                            ConjunctiveNormalFormPropositionalTemporalLogicFormulaInfo] = None
    output: OutputStatistics = None


@dataclass
class TestSuiteStatistics(DataClassJsonMixin):
    program_name: str
    program_version: str
    test_run: List[TestRunStatistics] = field(default_factory=list)


@dataclass
class Statistics(DataClassJsonMixin):
    test_suites: List[TestSuiteStatistics] = field(default_factory=list)
    date: datetime.datetime = datetime.datetime.now()
    hardware: HardwareStatistics = HardwareStatistics()
