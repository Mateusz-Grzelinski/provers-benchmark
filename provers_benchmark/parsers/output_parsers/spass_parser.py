from typing import Optional

from provers_benchmark.parsers.parsers import OutputParser
from provers_benchmark.statistics.stats import SATStatus


class SpassParser(OutputParser):
    @staticmethod
    def parse_output(returncode: int, stdout: Optional[str], stderr: Optional[str]) -> SATStatus:
        """SPASS is an automated theorem prover for first-order logic with equality.
          So the input for the prover is a first-order formula in our syntax.
          Running SPASS on such a formula results in the final output SPASS beiseite: Proof found.
          if the formula is valid,  SPASS beiseite: Completion found.
          if the formula is not valid and because validity in first-order logic is undecidable,
          SPASS may run forever without producing any final result.
          """
        if 'SPASS beiseite: Proof found' in stdout:
            return SATStatus.SATISFIABLE
        elif 'SPASS beiseite: Completion found' in stdout:
            return SATStatus.UNSATISFIABLE
        return SATStatus.UNKOWN
