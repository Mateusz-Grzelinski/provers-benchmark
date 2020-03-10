import argparse
import csv
import os
import sys
import time
from collections import Counter
from enum import Enum
from itertools import chain

from dataclasses_json import DataClassJsonMixin
from dataclasses import is_dataclass, asdict

from provers_benchmark.config import read_config, TestInput, Translator
from provers_benchmark.benchmark import run_benchmark, translate
from provers_benchmark.utils import command_name, find_translator
from provers_benchmark.log import init_log, get_logger
from provers_benchmark.statistics.stats import Statistics, SATStatus, TestRunStatistics


def parse_args():
    parser = argparse.ArgumentParser(prog="Provers Benchmark",
                                     description="Benchmark for testing provers")
    parser.add_argument("-v", "--version", action="version",
                        version="%(prog)s Pre-alpha 0.1",
                        help="Prints current version")
    parser.add_argument("-f", "--file", default="config.yaml", help="config file")

    return parser.parse_args()


def save_stats_to_json(path):
    out_file = path + '.json'
    logger.info(f'writing results to {out_file}')
    with open(out_file, 'w') as outfile:
        outfile.write(stats.to_json())


def save_stats_to_csv(path):
    out_file = path + '.csv'
    logger.info(f'writing results to {out_file}')
    with open(out_file, 'w') as csv_file:
        rows = []
        for test_run in stats.test_runs:
            test_run_dict = test_run.to_dict()
            del test_run_dict['output']['stderr']
            del test_run_dict['output']['stdout']
            more_nested_items = True
            while more_nested_items:
                more_nested_items = False
                for key, val in test_run_dict.copy().items():
                    if isinstance(val, Enum):
                        test_run_dict[key] = val.value
                    elif isinstance(val, dict):
                        more_nested_items = True
                        for nested_key, item in val.items():
                            test_run_dict[key + '.' + nested_key] = item
                        del test_run_dict[key]
                    elif isinstance(val, DataClassJsonMixin):
                        more_nested_items = True
                        for nested_key, item in val.to_dict():
                            test_run_dict[key + '.' + nested_key] = item
                        del test_run_dict[key]
                    elif is_dataclass(val):
                        more_nested_items = True
                        for nested_key, item in asdict(val):
                            test_run_dict[key + '.' + nested_key] = item
                        del test_run_dict[key]

            rows.append(test_run_dict)
        all_keys_in_csv = set().union(*[list(row.keys()) for row in rows])
        csv_writer = csv.DictWriter(csv_file, fieldnames=sorted(all_keys_in_csv))
        csv_writer.writeheader()
        for row in rows:
            csv_writer.writerow(row)

    logger.info(f'Benchmark was running for {time.time() - start:.2f} seconds in total')


if __name__ == '__main__':
    args = parse_args()
    init_log()
    logger = get_logger()

    config = read_config(args.file)
    if config:
        if errors := config.validate():
            for e in errors:
                logger.error(e)
            logger.error('Errors in config. Aborting')
            sys.exit(1)

    inputs = len(config.test_inputs)
    translators = len(config.translators)
    files = sum(len(test_inputs.files) for test_inputs in config.test_inputs)
    test_suites = len(config.test_suites)
    # test_cases = sum(len(test_suite.test_runs) for test_suite in config.test_suites)
    logger.info(f'Starting with {inputs} inputs, '
                f'{translators} translators, '
                f'{files} files, '
                f'{test_suites} test suites, ')

    start = time.time()
    stats = Statistics()
    for test_suite in config.test_suites:
        for test_input in config.test_inputs:
            for file in test_input.files:
                minimal_statistics, formula_info = test_input.get_file_statistics(file)
                if test_suite.required_format != test_input.format:
                    translator = find_translator(from_format=test_input.format, to_format=test_suite.required_format,
                                                 available_translators=config.translators)
                    file = translate(translator=translator, input_file=file)
                    minimal_statistics.translated_with = translator
                exec_stats, out_stats = run_benchmark(test_suite, input_path=file, timeout=config.general.test_timeout)
                stats.test_runs.append(
                    TestRunStatistics(name=test_suite.name,
                                      program_name=os.path.basename(command_name(test_suite.command)),
                                      program_version=test_suite.version,
                                      command=test_suite.command, execution_statistics=exec_stats,
                                      minimal_input_statistics=minimal_statistics,
                                      input_formula_statistics=formula_info, output=out_stats
                                      )
                )

    statuses = [i.output.status for i in stats.test_runs]
    c = Counter(statuses)
    unsat = len([i for i in stats.test_runs if i.output.status == SATStatus.UNSATISFIABLE])
    logger.info(f'{c[SATStatus.SATISFIABLE]} tests were SATisfiable, '
                f'{c[SATStatus.UNSATISFIABLE]} were UNSATisfiable, '
                f'{c[SATStatus.TIMEOUT]} ended with timeout, '
                f'{c[SATStatus.OUT_OF_MEMORY]} went out of memory, '
                f'{c[SATStatus.ERROR]} ended with error, '
                f'{c[SATStatus.UNKOWN]} are unknown. ')

    if dir := os.path.dirname(config.general.result_path):
        os.makedirs(dir, exist_ok=True)

    if config.general.result_as_json:
        save_stats_to_json(config.general.result_path)
    if config.general.result_as_csv:
        save_stats_to_csv(config.general.result_path)
