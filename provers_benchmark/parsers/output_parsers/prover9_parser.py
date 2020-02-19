from typing import Optional

from provers_benchmark.parsers.parsers import OutputParser
from provers_benchmark.statistics.stats import SATStatus


class Prover9Parser(OutputParser):
    @staticmethod
    def parse_output(returncode: int, stdout: Optional[str], stderr: Optional[str]) -> SATStatus:
        """Prover9: Exit Code	Reason for Termination (from https://www.cs.unm.edu/~mccune/prover9/manual/2009-11A/)
        0 (MAX_PROOFS) 	The specified number of proofs (max_proofs) was found.
        1 (FATAL) 	A fatal error occurred (user's syntax error or Prover9's bug).
        2 (SOS_EMPTY) 	Prover9 ran out of things to do (sos list exhausted).
        3 (MAX_MEGS) 	The max_megs (memory limit) parameter was exceeded.
        4 (MAX_SECONDS) 	The max_seconds parameter was exceeded.
        5 (MAX_GIVEN) 	The max_given parameter was exceeded.
        6 (MAX_KEPT) 	The max_kept parameter was exceeded.
        7 (ACTION) 	A Prover9 action terminated the search.
        101 (SIGINT) 	Prover9 received an interrupt signal.
        102 (SIGSEGV) 	Prover9 crashed, most probably due to a bug.
        """

        # todo implement parser (if these ifs are not enough)
        # partial prover9 parser
        # prover9 exits with 2 if search failed
        if returncode == 0:
            return SATStatus.SATISFIABLE
        elif returncode == 1:
            return SATStatus.ERROR
        elif returncode == 4:
            return SATStatus.TIMEOUT
        else:
            return SATStatus.UNSATISFIABLE
