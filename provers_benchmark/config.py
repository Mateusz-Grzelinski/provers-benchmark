from __future__ import annotations

import glob
import json
import logging
import os
from dataclasses import dataclass
from enum import Enum, EnumMeta
from functools import partial
from typing import Optional, Dict, List, Type, Tuple

import dacite
import yaml

from provers_benchmark.errors import BenchmarkConfigException, DaciteArgumentValueError, UnsupportedSolver
from provers_benchmark.parsers.parsers import get_all_output_parsers
from provers_benchmark.statistics.stats import MinimalSATStatistics
from provers_benchmark.utils import command_name, which, find_translator

logger: logging.Logger = logging.getLogger('BenchmarkConfig')

INPUT_PATH_TEMPLATE = '$INPUT_PATH'
OUTPUT_PATH_TEMPLATE = '$OUTPUT_PATH'
CACHE_LOCATION = '.cache'


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


def _safe_enum_cast(enum: Type[Enum], argument: str, ):
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


@dataclass
class Translator:
    """Translate text to different syntax by calling executable
    by default input file is piped to stdin, stdout is piped to output file
    if input_as_last_argument is True, input_filename will be last arguments
    input_as_last_argument and input_after_option are mutually exclusive
    """
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
        if not which(command_name(self.command)):
            errors.append(BenchmarkConfigException(f'command is not found',
                                                   field_paths={'command': self.command}))
        _check_input_mode(input_mode=self.input_mode, command=self.command)
        _check_output_mode(output_mode=self.output_mode, command=self.command)
        return errors


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
        if not which(command_name(self.command)):
            errors.append(BenchmarkConfigException(f'command is not found',
                                                   field_paths={'command': self.command}))

        probably_executable_name = os.path.basename(self.command.split()[0])
        if probably_executable_name.lower() not in get_all_output_parsers():
            errors.append(UnsupportedSolver(field_paths={'command': self.command}, solver=probably_executable_name))

        if e := _check_input_mode(self.input_mode, self.command):
            errors.append(e)
        return errors


@dataclass
class TestInput:
    patterns: List[str]
    """list of paths, recursive wildcards supported"""
    format: str
    name: Optional[str] = ''
    """Unique TestInput name. Leave empty to generate automatically"""

    def __post_init__(self):
        if not self.name:
            self.name = f'{self.format}-{id(self)}'

    def validate(self) -> List[BenchmarkConfigException]:
        errors = []
        for pattern in self.patterns:
            if not glob.glob(pattern, recursive=True):
                errors.append(BenchmarkConfigException(f'file pattern {pattern} did not match any files',
                                                       field_paths={'files': self.files}))

        return errors

    @property
    def files(self):
        files = []
        for pattern in self.patterns:
            files.extend(glob.glob(pattern, recursive=True))
        return files

    def get_file_statistics(self, file_path: str) -> Tuple[MinimalSATStatistics, Dict]:
        min_stats = MinimalSATStatistics(name=self.name, path=file_path, format=self.format)

        try:
            with open(file_path + '.json') as formula_info_file:
                formula_info = json.load(formula_info_file)
            return min_stats, formula_info
        except FileNotFoundError:
            logger.warning(
                f'Statistics for {os.path.abspath(file_path)} not available (not found file {os.path.abspath(file_path)}.json)')

        return min_stats, {}


@dataclass
class GeneralConfig:
    result_path: str
    result_as_json: bool = True
    result_as_csv: bool = True
    test_timeout: int = 300


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


def read_config(path: str) -> Optional[BenchmarkConfig]:
    logger.info(f'Reading config file: {os.path.abspath(path)}')
    dacite_config = dacite.Config(check_types=True, strict=True,
                                  type_hooks={
                                      InputMode: partial(_safe_enum_cast, InputMode),
                                      OutputMode: partial(_safe_enum_cast, OutputMode)
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
