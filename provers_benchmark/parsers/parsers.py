from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Union, Optional


class StatisticParser(ABC):
    @staticmethod
    @abstractmethod
    def get_file_input_statistics(file_path: str) -> SATStatistics:
        pass


class OutputParser(ABC):
    @staticmethod
    @abstractmethod
    def parse_output(returncode: int, stdout: Optional[str], stderr: Optional[str]) -> SATStatus:
        pass


class Formats(Enum):
    TPTP = 'tptp'
    LADR = 'ladr'
    INKRESAT = 'inkresat'
    """with .fml extension"""


class Solvers(Enum):
    PROVER9 = 'prover9'
    SPASS = 'spass'
    INKRESAT = 'inkresat'


def get_statistics_parser(format_name: Union[str, Formats]) -> Optional[InputParser]:
    format_name = format_name.lower()
    from provers_benchmark.parsers.statistics_parsers.tptp_parser import TPTPParser
    from provers_benchmark.parsers.statistics_parsers.inkresat_cnf_json_parser import InkresatCNFPTLStatisticParser
    __format_info_lookup = {
        Formats.TPTP: TPTPParser,
        Formats.TPTP.value: TPTPParser,
        Formats.LADR: None,
        Formats.LADR.value: None,
        Formats.INKRESAT: InkresatCNFPTLStatisticParser,
        Formats.INKRESAT.value: InkresatCNFPTLStatisticParser,
    }
    key = format_name
    if isinstance(key, str):
        key = format_name.lower()
    return __format_info_lookup.get(key)


def get_output_parser(solver: Union[str, Solvers]) -> Optional[OutputParser]:
    from provers_benchmark.parsers.output_parsers.prover9_parser import Prover9Parser
    from provers_benchmark.parsers.output_parsers.spass_parser import SpassParser
    from provers_benchmark.parsers.output_parsers.inkresat_parser import InkresatParser
    __solvers_lookup_table = {
        Solvers.PROVER9: Prover9Parser,
        Solvers.PROVER9.value: Prover9Parser,
        Solvers.SPASS: SpassParser,
        Solvers.SPASS.value: SpassParser,
        Solvers.INKRESAT: InkresatParser,
        Solvers.INKRESAT.value: InkresatParser,
    }
    key = solver
    if isinstance(key, str):
        key = solver.lower()
    return __solvers_lookup_table.get(key)
