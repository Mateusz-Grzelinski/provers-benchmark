from typing import Optional

from provers_benchmark.parsers.parsers import OutputParser
from provers_benchmark.statistics.stats import SATStatus


class InkresatParser(OutputParser):
    @staticmethod
    def parse_output(returncode: int, stdout: Optional[str], stderr: Optional[str]) -> SATStatus:
        """Inkresat example output:
        variables added: 1
        clauses added: 1
        SAT cycles: 1
        pattern store hits: 0
        pattern store misses: 0
        time: 9.79900360107e-05
        SATISFIABLE
        """
        if returncode != 0:
            return SATStatus.ERROR
        if 'SATISFIABLE' in stdout:
            return SATStatus.SATISFIABLE
        elif 'UNSATISFIABLE' in stdout:
            return SATStatus.UNSATISFIABLE
        return SATStatus.UNKOWN
