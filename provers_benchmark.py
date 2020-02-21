import argparse
import csv
import time

from provers_benchmark.benchmark import Benchmark
from provers_benchmark.config import Config
from provers_benchmark.log import init_log, get_logger
from provers_benchmark.tests import TestInput


def parse_args():
    parser = argparse.ArgumentParser(prog="Provers Benchmark",
                                     description="Benchmark for testing provers")
    parser.add_argument("-v", "--version", action="version",
                        version="%(prog)s Pre-alpha 0.1",
                        help="Prints current version")
    parser.add_argument("-f", "--file", default="config.toml", help="config file")

    return parser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    init_log()
    logger = get_logger()

    config = Config(config_file=args.file)
    config.load_config()
    inputs = len(config.test_inputs)
    translators = len(TestInput.translators)
    files = sum(len(test_inputs.files) for test_inputs in config.test_inputs)
    test_suites = len(config.test_suites)
    test_cases = sum(len(test_suite.test_runs) for test_suite in config.test_suites)
    logger.info(f'Starting with {inputs} inputs, '
                f'{translators} translators, '
                f'{files} files, '
                f'{test_suites} test suites, '
                f'{test_cases} test cases')

    start = time.time()
    benchmark = Benchmark(test_suite=config.test_suites)
    if config.test_case_timeout:
        Benchmark.test_case_timeout = config.test_case_timeout
    stats = benchmark.run()

    out_file = config.output_dir if config.output_dir.endswith('.json') else config.output_dir + '.json'
    logger.info(f'writing results to {out_file}')
    with open(out_file, 'w') as outfile:
        outfile.write(stats.to_json())

    out_file = config.output_dir if config.output_dir.endswith('.csv') else config.output_dir + '.csv'
    logger.info(f'writing results to {out_file}')
    with open(out_file, 'w') as csv_file:
        rows = []
        for test_suite in stats.test_suites:
            for test_run in test_suite.test_run:
                test_run_dict = test_run.to_dict()
                test_run_dict['command'] = ' '.join(i for i in test_run.command)
                for attr_name in 'minimal_input_statistics', 'execution_statistics', 'input_statistics', 'output':
                    del test_run_dict[attr_name]
                    for key, item in getattr(test_run, attr_name).to_dict().items():
                        test_run_dict[attr_name + '.' + key] = item
                test_run_dict['input_statistics.clause_sizes'] = ';'.join(
                    f'{key}:{val}' for key, val in test_run.input_statistics.clause_sizes.items())
                rows.append(test_run_dict)
        csv_writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        csv_writer.writeheader()
        for row in rows:
            csv_writer.writerow(row)

    logger.info(f'Benchmark was running for {time.time() - start:.2f} seconds in total')
