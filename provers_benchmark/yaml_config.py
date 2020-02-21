from __future__ import annotations

import datetime
import glob
import os
from pprint import pprint
from typing import Set, Optional, Any, Dict, List

import yaml
from dataclasses import dataclass, asdict, replace, field, Field
import subprocess
import dacite
import logging

from provers_benchmark.errors import BenchmarkConfigException
from provers_benchmark.parsers.parsers import Formats, get_all_supported_formats, get_all_supported_parsers

logger: logging.Logger = logging.getLogger('BenchmarkConfig')
logger.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter(f'%(name)s:%(levelname)s:%(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

INPUT_PATH_TEMPLATE = '$INPUT_PATH'
OUTPUT_PATH_TEMPLATE = '$OUTPUT_PATH'


def _is_executable(command: str):
    try:
        subprocess.Popen([command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True).communicate()
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            return False
    return True


def _log_child_key_error(parent_key: str, e: BenchmarkConfigException):
    message = []
    for key, value in e.failing_keys.items():
        message.append(f'{parent_key}.{key}={value}')
    message = ', '.join(message)
    logger.error(f'{str(e)} ({message})')


@dataclass
class TestSuite:
    name: str
    """Unique TestSuite name"""
    command: str
    """Command to benchmark. Evaluated by shell. String $INPUT_PATH will be switched with real input path.
    Spaces in command path are not supported
    """
    required_format: str
    input_as_stdin: bool = True
    """if True test file will be provided on stdin, 
    else string $INPUT_PATH in command will be replaces with real path 
    """
    version: str = ''
    save_stdout: bool = True
    """Append standard output of command to statistics"""
    save_stderr: bool = True
    """Append standard error of command to statistics"""

    def validate(self) -> List[BenchmarkConfigException]:
        errors = []

        if not _is_executable(self.command):
            errors.append(
                BenchmarkConfigException(f'command is not executable', failing_keys={'command': self.command}))

        probably_executable_name = os.path.basename(self.command.split()[0])
        if probably_executable_name.lower() not in get_all_supported_parsers():
            errors.append(
                BenchmarkConfigException(
                    f'solver {probably_executable_name} is not supported. Use one of {get_all_supported_parsers()} or add '
                    f'it in provers_benchmark/parsers/output_parsers',
                    failing_keys={'command': self.command})
            )
        if self.input_as_stdin and INPUT_PATH_TEMPLATE in self.command:
            errors.append(
                BenchmarkConfigException(
                    f'you probably don\'t want to use both {INPUT_PATH_TEMPLATE} and set input_as_stdin',
                    failing_keys={'command': self.command, 'input_as_stdin': self.input_as_stdin})
            )
        return errors


@dataclass
class TestInput:
    cwd: Optional[str]
    """change working directory, defaults to current script path"""
    files: List[str]
    """list of paths, recursive wildcards supported"""
    format: str
    name: Optional[str] = ''
    """Unique TestInput name. Leave empty to generate automatically"""

    def __post_init__(self):
        if not self.name:
            self.name = f'{self.format}-{id(self)}'

    def validate(self) -> List[BenchmarkConfigException]:
        errors = []
        if not os.path.exists(self.cwd):
            errors.append(
                BenchmarkConfigException(f'path {os.path.abspath(self.cwd)} does not exists',
                                         failing_keys={'cwd': self.cwd})
            )
        for file_pattern in self.files:
            files = glob.glob(os.path.join(self.cwd, file_pattern))
            if not files:
                errors.append(
                    BenchmarkConfigException(f'file pattern {file_pattern} did not match any files',
                                             failing_keys={'files': self.files})
                )
        return errors


@dataclass
class Translator:
    from_format: str
    to_format: str
    command: str
    """External command that will translate formats.
    String $INPUT_PATH will be replaced with real input path, string $OUPUT_PATH will be replaced with read_output_path
    spaces in command path are not supported
    """
    input_as_stdin: bool
    """Input file will be provided to standart input"""
    output_as_stdout: bool
    """Assumes translated formula is on standard output"""

    def validate(self) -> List[BenchmarkConfigException]:
        errors = []
        if not _is_executable(self.command):
            errors.append(
                BenchmarkConfigException('command is not executable', failing_keys={'command': self.command})
            )
        if self.input_as_stdin and INPUT_PATH_TEMPLATE in self.command:
            errors.append(
                BenchmarkConfigException(
                    f'you probably don\'t want to use both {INPUT_PATH_TEMPLATE} and set input_as_stdin',
                    failing_keys={'command': self.command, 'input_as_stdin': self.input_as_stdin})
            )
        if self.output_as_stdout and OUTPUT_PATH_TEMPLATE in self.command:
            errors.append(
                BenchmarkConfigException(
                    f'you probably don\'t want to use both {OUTPUT_PATH_TEMPLATE} and set outpu_as_stdout',
                    failing_keys={'command': self.command, 'output_as_stdout': self.output_as_stdout})
            )
        return errors


@dataclass
class GeneralConfig:
    result_path: str
    result_as_json: bool = True
    result_as_csv: bool = True
    test_timeout: int = 300
    global_working_directory: str = '.'
    translator_cache_dir: str = '.cache'

    def validate(self) -> List[BenchmarkConfigException]:
        errors = []
        if not os.path.exists(self.global_working_directory):
            errors.append(
                BenchmarkConfigException(f'global_working_directory does not exist',
                                         failing_keys={'global_working_directory': self.global_working_directory})
            )
        return errors


def find_translator(from_format: str, to_format: str, available_translators: List[Translator]):
    # todo
    pass


@dataclass
class Benchmark:
    general: GeneralConfig
    translators: Optional[List[Translator]]
    test_inputs: List[TestInput]
    test_suites: List[TestSuite]

    def validate(self):
        for t in self.translators:
            for e in t.validate():
                _log_child_key_error(parent_key='translators', e=e)

        for t in self.test_inputs:
            for e in t.validate():
                _log_child_key_error(parent_key='test_inputs', e=e)

        test_input_names = [t.name for t in self.test_inputs]
        repeated_names = {'name': name for name in set(test_input_names) if test_input_names.count(name) > 1}
        if repeated_names:
            _log_child_key_error(parent_key='test_input',
                                 e=BenchmarkConfigException(f'value test_input.name must be unique',
                                                            failing_keys=repeated_names)
                                 )

        for t in self.test_suites:
            for e in t.validate():
                _log_child_key_error(parent_key='test_suites', e=e)

        for test_suite in self.test_suites:
            for test_input in self.test_inputs:
                if test_suite.required_format != test_input.format and not find_translator(
                        from_format=test_input.format, to_format=test_suite.required_format,
                        available_translators=self.translators):
                    logger.error(
                        f'Translation of input "{test_input.name}" from {test_input.format} to {test_suite.required_format} is not possible')


def read_config(path='template/config.yaml') -> Benchmark:
    logger.info(f'Reading config file: {os.path.abspath(path)}')
    dacite_config = dacite.Config(check_types=True, strict=True)
    with open(path, 'r') as config_file:
        config = yaml.safe_load(config_file)
    try:
        b_conf = dacite.from_dict(data_class=Benchmark, data=config, config=dacite_config)
        return b_conf
    except dacite.UnexpectedDataError as e:
        logger.error(f'Unused keys: {e.keys}')
    except dacite.WrongTypeError as e:
        logger.error(f'{str(e)}, ({e.field_path}={e.value})')


if __name__ == '__main__':
    b_conf = read_config()
    if b_conf:
        b_conf.validate()
