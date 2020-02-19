from __future__ import annotations

import os
from dataclasses import dataclass, field, InitVar
from typing import List

from provers_benchmark.errors import BenchmarkException
from provers_benchmark.log import get_logger
from provers_benchmark.statistics.stats import TestSuiteStatistics
from provers_benchmark.tests.test_input import TestInput

logger = get_logger()

@dataclass
class TestSuite:
    name: str
    executable: str
    cwd: InitVar[str] = os.getcwd()
    PATH: str = None
    capture_stdout: bool = True
    version: str = None
    options: List[str] = field(default_factory=list)
    test_runs: List[TestRun] = field(default_factory=list)
    test_inputs: List[TestInput] = field(default_factory=list)

    def __post_init__(self, cwd):
        if self.PATH is not None and not os.path.isabs(self.PATH):
            self.PATH = os.path.abspath(os.path.join(cwd, self.PATH))

        # todo warn if PATH does not exits
        # todo check if all formats are achievable (static method?) also unify this with Config

    def run(self) -> TestSuiteStatistics:
        """Synchronously run all test cases defined in this test suite"""
        from provers_benchmark.tests import TestRun
        test_suite_stats = TestSuiteStatistics(program_name=self.executable, program_version=self.version)
        for test_run in self.test_runs:
            try:
                for test_input in test_run.filter_inputs(self.test_inputs):
                    test_run: TestRun
                    test_run_stats = test_run.run(executable=self.executable, options=self.options, PATH=self.PATH,
                                                  test_input=test_input, capture_stdout=self.capture_stdout)
                    test_suite_stats.test_run.extend(test_run_stats)
            except BenchmarkException as e:
                logger.error(e)
                continue
            except KeyboardInterrupt:
                logger.info("Keyboard interrupt")
                continue

        yield test_suite_stats
