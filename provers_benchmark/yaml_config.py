from __future__ import annotations

import datetime
import glob
import os
import sys
from enum import Enum, EnumMeta
from functools import partial
from pprint import pprint
from typing import Set, Optional, Any, Dict, List, Literal, Union, Type

import yaml
from dataclasses import dataclass, asdict, replace, field, Field
import subprocess
import dacite
import logging

from provers_benchmark.errors import BenchmarkConfigException, DaciteArgumentValueError, UnsupportedSolver
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


class __OutputEnumMeta(EnumMeta):
    """Gives a unique type for OutputMode (required by dacite)"""
    pass


class __InputEnumMeta(EnumMeta):
    """Gives a unique type for InputMode (required by dacite)"""
    pass


class OutputMode(Enum, metaclass=__OutputEnumMeta):
    STDOUT = 'stdout'
    ARGUMENT = 'argument'


class InputMode(Enum, metaclass=__InputEnumMeta):
    STDIN = 'stdin'
    ARGUMENT = 'argument'


def safe_enum_cast(enum: Type[Enum], argument: str, ):
    try:
        return enum(argument)
    except ValueError:
        raise DaciteArgumentValueError(available_values=[i.value for i in enum], current_value=argument)


def _check_input_mode(input_mode: InputMode, command: str):
    failing_keys = {'command': command, 'input_mode': input_mode}
    if input_mode == InputMode.STDIN and INPUT_PATH_TEMPLATE in command:
        return BenchmarkConfigException(
            f'you can not use input_mode "stdin" with specified {INPUT_PATH_TEMPLATE} in command',
            field_paths=failing_keys
        )
    if input_mode == InputMode.ARGUMENT and INPUT_PATH_TEMPLATE not in command:
        return BenchmarkConfigException(
            f'when using input_mode "argument", you must specify {INPUT_PATH_TEMPLATE} in command',
            field_paths=failing_keys
        )


def _check_output_mode(output_mode: OutputMode, command: str):
    failing_keys = {'command': command, 'output_mode': output_mode}
    if output_mode == OutputMode.STDOUT and OUTPUT_PATH_TEMPLATE in command:
        return BenchmarkConfigException(
            f'you can not use output_mode "{OutputMode.STDOUT}" with specified {OUTPUT_PATH_TEMPLATE} in command',
            field_paths=failing_keys
        )
    if output_mode == OutputMode.ARGUMENT and INPUT_PATH_TEMPLATE not in command:
        return BenchmarkConfigException(
            f'when using output_mode "{OutputMode.ARGUMENT}", you must specify {OUTPUT_PATH_TEMPLATE} in command',
            field_paths=failing_keys
        )


def _is_executable(command: str):
    try:
        subprocess.Popen([command], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=True).communicate(
            timeout=1)
    except OSError as e:
        if e.errno == os.errno.ENOENT:
            return False
    except subprocess.TimeoutExpired:
        return True
    return True


def find_translator(from_format: str, to_format: str, available_translators: List[Translator]):
    for translator in available_translators:
        if translator.from_format == from_format and translator.to_format == to_format:
            return translator


@dataclass
class TestSuite:
    name: str
    """Unique TestSuite name"""
    command: str
    """Command to benchmark. Evaluated by shell. String $INPUT_PATH will be switched with real input path.
    Spaces in command path are not supported
    """
    required_format: str
    input_mode: InputMode
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
            errors.append(BenchmarkConfigException(f'command is not executable', field_paths={'command': self.command}))

        probably_executable_name = os.path.basename(self.command.split()[0])
        if probably_executable_name.lower() not in get_all_supported_parsers():
            errors.append(UnsupportedSolver(field_paths={'command': self.command}, solver=probably_executable_name))

        if e := _check_input_mode(self.input_mode, self.command):
            errors.append(e)
        return errors


@dataclass
class TestInput:
    path: Optional[str]
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
        if not os.path.exists(self.path):
            errors.append(BenchmarkConfigException(f'path {os.path.abspath(self.path)} does not exists',
                                                   field_paths={'path': self.path}))
        for file_pattern in self.files:
            files = glob.glob(os.path.join(self.path, file_pattern))
            if not files:
                errors.append(BenchmarkConfigException(f'file pattern {file_pattern} did not match any files',
                                                       field_paths={'files': self.files}))
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
    input_mode: InputMode
    output_mode: OutputMode

    def validate(self) -> List[BenchmarkConfigException]:
        errors = []
        if not _is_executable(self.command):
            errors.append(BenchmarkConfigException('command is not executable', field_paths={'command': self.command}))
        _check_input_mode(input_mode=self.input_mode, command=self.command)
        _check_output_mode(output_mode=self.output_mode, command=self.command)
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
                                         field_paths={'global_working_directory': self.global_working_directory})
            )
        return errors


@dataclass
class BenchmarkConfig:
    general: GeneralConfig
    translators: Optional[List[Translator]]
    test_inputs: List[TestInput]
    test_suites: List[TestSuite]

    def validate(self) -> List[BenchmarkConfigException]:
        errors = []
        for t in self.translators:
            for e in t.validate():
                e.update_field_path('translators')
                errors.append(e)

        for t in self.test_inputs:
            for e in t.validate():
                e.update_field_path('test_inputs')
                errors.append(e)

        test_input_names = [t.name for t in self.test_inputs]
        repeated_names = {'name': name for name in set(test_input_names) if test_input_names.count(name) > 1}
        if repeated_names:
            e = BenchmarkConfigException(f'value test_input.name must be unique',
                                         field_paths=repeated_names)
            e.update_field_path('test_input')
            errors.append(e)

        for t in self.test_suites:
            for e in t.validate():
                e.update_field_path('test_inputs')
                errors.append(e)

        for test_suite in self.test_suites:
            for test_input in self.test_inputs:
                if test_suite.required_format != test_input.format and not find_translator(
                        from_format=test_input.format, to_format=test_suite.required_format,
                        available_translators=self.translators):
                    errors.append(BenchmarkConfigException(
                        f'Translation of input "{test_input.name}" from {test_input.format} to {test_suite.required_format} in "{test_suite.name}" is not possible',
                        field_paths={'test_suite': test_suite, 'test_input': test_input}
                    ))
        return errors


def read_config(path='../template/config.yaml') -> Optional[BenchmarkConfig]:
    logger.info(f'Reading config file: {os.path.abspath(path)}')
    dacite_config = dacite.Config(check_types=True, strict=True,
                                  type_hooks={
                                      InputMode: partial(safe_enum_cast, InputMode),
                                      OutputMode: partial(safe_enum_cast, OutputMode)
                                  })
    with open(path, 'r') as config_file:
        config = yaml.safe_load(config_file)
    try:
        config = dacite.from_dict(data_class=BenchmarkConfig, data=config, config=dacite_config)
    except dacite.UnexpectedDataError as e:
        logger.error(f'Unused keys: {e.keys}')
    except dacite.WrongTypeError as e:
        logger.error(f'{str(e)}, ({e.field_path}={e.value})')
    except DaciteArgumentValueError as e:
        logger.error(e)
    else:
        logger.info(f'Config syntax is correct')
        return config
    return None


if __name__ == '__main__':
    b_conf = read_config()
    if b_conf and (errors := b_conf.validate()):
        for e in errors:
            logger.error(e)
        sys.exit(1)
