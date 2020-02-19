import argparse
import json
import time

from provers_benchmark.benchmark import Benchmark
from provers_benchmark.config import Config
from provers_benchmark.log import init_log, get_logger
from provers_benchmark.statistics.json_encoder import ClassAsDictJSONEncoder
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
    with open(config.output_dir, 'w') as outfile:
        logger.info(f'writing results to {config.output_dir}')
        json.dump(stats, outfile, indent=2, cls=ClassAsDictJSONEncoder)
    logger.info(f'Benchmark was running for {time.time() - start:.2f} seconds in total')
