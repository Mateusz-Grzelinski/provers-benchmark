import logging
import os
import subprocess
import time

import psutil

from provers_benchmark.config import Translator, InputMode, OutputMode, TestSuite, CACHE_LOCATION
from provers_benchmark.non_blocking_stream_reader import NonBlockingStreamReader
from provers_benchmark.parsers import find_output_parser
from provers_benchmark.statistics.monitored_process import MonitoredProcess
from provers_benchmark.statistics.stats import OutputStatistics, SATStatus
from provers_benchmark.utils import build_command, command_name, executable_name

logger = logging.getLogger('ProverBenchmark')


def get_cache_location(translator: Translator, input_file: str):
    command = os.path.basename(command_name(translator.command))
    cache_dir = os.path.join(CACHE_LOCATION, command, f'{translator.from_format}-{translator.to_format}')
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, str(hash(input_file)))


def translate(translator: Translator, input_file: str):
    output_file = get_cache_location(translator=translator, input_file=input_file)

    command = build_command(translator.command, input_file, translator.input_mode, output_file, translator.output_mode)
    stdin = subprocess.DEVNULL if translator.input_mode == InputMode.ARGUMENT else open(input_file)
    stdout = subprocess.DEVNULL if translator.output_mode == OutputMode.ARGUMENT else open(output_file, 'w')
    p = subprocess.Popen(command, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE, shell=True, text=True)
    out, err = p.communicate()
    if p.returncode == 0:
        logger.info(f'Translated {input_file} to {output_file} from {translator.from_format} to {translator.to_format}')
        return output_file
    else:
        logger.error(f'error in translating "{command}": {err}')
        return None, err


def run_benchmark(test_suite: TestSuite, input_path: str, timeout: int):
    logger.info(f'Benchmarking: "{test_suite.name}" with input "{input_path}"')
    out_stats = OutputStatistics()
    command = build_command(test_suite.command, input_path, test_suite.input_mode, output_file=None, output_mode=None)
    stdin = subprocess.DEVNULL if test_suite.input_mode == InputMode.ARGUMENT else open(input_path)
    with MonitoredProcess(command, stdin=stdin, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, shell=True) as proc:
        nbsr_stdout = NonBlockingStreamReader(stream=proc.stdout)
        nbsr_stderr = NonBlockingStreamReader(stream=proc.stderr)
        last_read = time.time()
        while proc.poll() is None:
            time.sleep(0.1)
            if proc.exec_stats.execution_time > timeout:
                proc.kill()
                out_stats.status = SATStatus.TIMEOUT
                break
            if psutil.virtual_memory().free < 100 * 1024 * 1024:  # 100MB
                proc.kill()
                out_stats.status = SATStatus.OUT_OF_MEMORY
                break
            if time.time() - last_read > 1:
                out_stats.stdout = ''.join(nbsr_stdout.readall())
                out_stats.stderr = ''.join(nbsr_stderr.readall())
                last_read = time.time()
        out_stats.stdout += ''.join(nbsr_stdout.readall())
        # we want all stderr
        out_stats.stderr += ''.join(nbsr_stderr.readall())
    execution_statistics = proc.get_statistics()

    if out_stats.status not in {SATStatus.OUT_OF_MEMORY, SATStatus.TIMEOUT}:
        parser = find_output_parser(executable=executable_name(command))
        out_stats.status = parser.parse_output(returncode=execution_statistics.returncode, stdout=out_stats.stdout,
                                               stderr=out_stats.stderr)
    if not test_suite.save_stdout:
        out_stats.stdout = None
    if not test_suite.save_stderr:
        out_stats.stdout = None
    logger.info(f'Benchmarking done: returncode {execution_statistics.returncode}, '
                f'SAT: {out_stats.status}, '
                f'time: {execution_statistics.execution_time:.2f}"')
    return execution_statistics, out_stats
