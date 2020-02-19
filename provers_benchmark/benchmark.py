from __future__ import annotations

from dataclasses import dataclass
from typing import List, ClassVar

from provers_benchmark.log import get_logger
from provers_benchmark.statistics.stats import Statistics, SATStatus

logger = get_logger()


@dataclass
class Benchmark:
    test_suite: List[TestSuite]
    test_case_timeout: ClassVar[int] = 300

    def run(self) -> Statistics:
        statistics = Statistics()
        for test_suite in self.test_suite:
            test_suite_stats = test_suite.run()
            statistics.test_suites.extend(test_suite_stats)

        unsat = 0
        sat = 0
        timeout = 0
        different = 0
        for test_suite in statistics.test_suites:
            for test_run in test_suite.test_run:
                if test_run.output.status == SATStatus.TIMEOUT:
                    timeout += 1
                elif test_run.output.status == SATStatus.SATISFIABLE:
                    sat += 1
                elif test_run.output.status == SATStatus.UNSATISFIABLE:
                    unsat += 1
                else:
                    different += 1
        logger.info(f'{sat} tests were satisfiable, {unsat} were unsat, {timeout} were timeout, '
                    f'{different} ended with different status')

        return statistics
