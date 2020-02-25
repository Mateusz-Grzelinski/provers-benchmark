from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Union, Optional

from provers_benchmark.statistics.stats import SATStatus


class OutputParser(ABC):
    @staticmethod
    @abstractmethod
    def parse_output(returncode: int, stdout: Optional[str], stderr: Optional[str]) -> SATStatus:
        pass


class Parsers(Enum):
    PROVER9 = 'prover9'
    SPASS = 'spass'
    INKRESAT = 'inkresat'


def get_all_output_parsers():
    return [i.value for i in Parsers]


def find_output_parser(executable: Union[str, Parsers]) -> Optional[OutputParser]:
    from provers_benchmark.parsers.output_parsers.prover9_parser import Prover9Parser
    from provers_benchmark.parsers.output_parsers.spass_parser import SpassParser
    from provers_benchmark.parsers.output_parsers.inkresat_parser import InkresatParser
    __solvers_lookup_table = {
        Parsers.PROVER9: Prover9Parser,
        Parsers.PROVER9.value: Prover9Parser,
        Parsers.SPASS: SpassParser,
        Parsers.SPASS.value: SpassParser,
        Parsers.INKRESAT: InkresatParser,
        Parsers.INKRESAT.value: InkresatParser,
    }
    key = executable
    if isinstance(key, str):
        key = executable.lower()
    return __solvers_lookup_table.get(key)
