import copy
import glob
import logging
import os
from dataclasses import dataclass, field
from pprint import pprint
from typing import List, Dict, Type, NoReturn

import toml

from provers_benchmark.errors import BenchmarkConfigException, BenchmarkException
from provers_benchmark.tests import TestRun, TestSuite, TestInput
from provers_benchmark.translators import Translator


@dataclass
class DictPoper:
    """Convenience class for removing items from dictionary
    use with context manager to print warning if dictionary was not emptied
    """

    def __init__(self, source: dict, logger: logging.Logger = logging, *args, **kwargs):
        """source is dictionry that will be consumed
        log any errors to logger
        args and kwargs are used for logging as context to provide more info where the error occured
         """
        self.source = source
        self._logger = logger
        self._log_context = []
        if args:
            self._log_context.extend(args)
        if kwargs:
            self._log_context.append(kwargs)
        self.errors_occured = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.source:
            message = f"Unknown keys: '{self.source}'"
            self._warning(message)

    def pop_key(self, variable: str, default: any = None, required: bool = False,
                type_check: Type = None):
        """Remove and return variable from source and:
        add default value if not in source
        log error if required and not in source
        set self.errors_occured if something went wrong
        """
        ok = True
        value = self.source.pop(variable, default)
        if required and value is None:
            ok = False
            message = f"Missing required key: '{variable}'"
            self._error(message)

        if value is not None and type_check is not None and type(value) != type_check:
            ok = False
            message = f"'{variable}'"
            f" should be {type_check.__name__},"
            f" but is {type(value).__name__}"
            self._error(message)

        if type_check == str and value is not None:
            value = value.strip()

        return value, ok

    @property
    def log_context(self) -> str:
        """Return context passed to class in __init__ method"""
        return ' '.join(map(str, self._log_context))

    def _error(self, message):
        self.errors_occured = True
        if self.log_context:
            message = f"{message}, in {self.log_context}"

        self._logger.error(message)

    def _warning(self, message):
        if self.log_context:
            message = f"{message}, in {self.log_context}"

        self._logger.warning(message)


@dataclass
class Config:
    config_file: str = 'config.toml'
    output_dir: str = 'benchmark-output'
    log_file: str = 'benchmark.log'
    test_suites: List[TestSuite] = field(default_factory=list)
    test_inputs: List[TestInput] = field(default_factory=list)
    test_case_timeout: int = None

    _load_errors_occured: bool = False
    _logger: logging.Logger = logging.getLogger('BenchmarkConfig')

    def __post_init__(self):
        self._logger.setLevel(logging.DEBUG)

    def load_config(self) -> NoReturn:
        """Load and config"""
        self._load_errors_occured = False
        if not os.path.isfile(self.config_file):
            raise BenchmarkException(f"Config file '{self.config_file}'' is not found/not a file")

        benchmark_config = toml.load(self.config_file)

        with DictPoper(benchmark_config, self._logger, self.config_file) as poper:
            general_config, _ = poper.pop_key('general', required=True, type_check=dict)
            self._load_general(general_config)
            translators_config, _ = poper.pop_key('translators', required=False, type_check=list)
            self._load_translators(translators_config)
            test_inputs_config, _ = poper.pop_key('testInputs', required=True, type_check=list)
            self._load_test_inputs(test_inputs_config)
            test_suites_config, _ = poper.pop_key('testSuites', required=True, type_check=list)
            self._load_test_suites(test_suites_config)

            if poper.errors_occured or self._load_errors_occured:
                self.test_inputs.clear()
                TestInput.translators.clear()
                self.test_suites.clear()
                raise BenchmarkConfigException("Errors occured in config. See log warnings and errors")
        self._logger.info("Config parsed successfully")

    def _load_general(self, general_config: Dict) -> NoReturn:
        with DictPoper(general_config, self._logger, "[general]", copy.deepcopy(general_config)) as poper:
            self.output_dir, _ = poper.pop_key(variable="output_dir",
                                               default=self.output_dir,
                                               required=False,
                                               type_check=str)

            self.test_case_timeout, _ = poper.pop_key(variable="test_case_timeout",
                                                      default=None,
                                                      required=False,
                                                      type_check=int)
            # todo check is is writeable (should be dir or file?

    def _load_translators(self, translators_config: List) -> NoReturn:
        if not translators_config:
            return
        for translator_config in translators_config:
            # for error reporting
            with DictPoper(translator_config, self._logger, "[[translators]]",
                           copy.deepcopy(translator_config)) as poper:
                from_format, _ = poper.pop_key(variable="from_format",
                                               required=True,
                                               type_check=str)

                to_format, _ = poper.pop_key(variable="to_format",
                                             required=True,
                                             type_check=str)

                options, _ = poper.pop_key(variable="options",
                                           default=[],
                                           required=False,
                                           type_check=list)

                input_after_option, _ = poper.pop_key(variable="input_after_option",
                                                      required=False,
                                                      type_check=str)

                input_as_last_argument, _ = poper.pop_key(variable="input_as_last_argument",
                                                          required=False,
                                                          type_check=bool)

                output_after_option, _ = poper.pop_key(variable="output_after_option",
                                                       required=False,
                                                       type_check=str)

                executable, _ = poper.pop_key(variable="executable",
                                              required=True,
                                              type_check=str)
                extension, _ = poper.pop_key(variable="extension",
                                             required=False)

                PATH, _ = poper.pop_key(variable="PATH",
                                        default=None,
                                        type_check=str)

                if poper.errors_occured:
                    continue
            try:
                translator = Translator(from_format=from_format,
                                        to_format=to_format,
                                        executable=executable,
                                        extension=extension,
                                        options=[option.strip() for option in options],
                                        input_as_last_argument=input_as_last_argument,
                                        input_after_option=input_after_option,
                                        output_after_option=output_after_option,
                                        PATH=PATH)
            except BenchmarkException as e:
                self._error(e)
            else:
                if any(translator.to_format == i.to_format for i in TestInput.translators):
                    self._logger.warning(
                        f"Multiple translators with the same output format are not supported, "
                        f"skipping {translator}")
                else:
                    TestInput.translators.append(translator)

    def _load_test_inputs(self, test_inputs_config: Dict) -> NoReturn:
        # test_inputs_config = config.pop("testInputs", None)
        if not test_inputs_config:
            self._error("You must define at least one testInput")
            return

        for test_input_config in test_inputs_config:
            with DictPoper(test_input_config, self._logger, "[[testInputs]]",
                           copy.deepcopy(test_input_config)) as poper:
                name, _ = poper.pop_key(variable="name",
                                        required=True,
                                        type_check=str)

                path, _ = poper.pop_key(variable="path",
                                        required=True,
                                        type_check=str)

                format, _ = poper.pop_key(variable="format",
                                          required=True,
                                          type_check=str)

                patterns, _ = poper.pop_key(variable="files",
                                            required=True,
                                            type_check=list)
                gather_statistics_from_json_file, _ = poper.pop_key(
                    variable="gather_statistics_from_json_file",
                    required=False, type_check=bool)
                gather_statistics_from_formula_file, _ = poper.pop_key(
                    variable="gather_statistics_from_formula_file",
                    required=False, type_check=bool)

                files = []
                prefix = path if os.path.isabs(path) else os.path.join(os.getcwd(), path)
                for pattern in patterns:
                    wildcard = os.path.join(prefix, pattern)
                    resolved_paths = glob.glob(wildcard, recursive=True)

                    if not resolved_paths:
                        self._logger.warning(f"pattern '{wildcard}' did not match any file")
                    else:
                        files.extend(resolved_paths)

                if not files:
                    self._error(f"no file defined for testInput")
                    continue

                if poper.errors_occured:
                    continue

            try:
                test_input = TestInput(
                    name=name, path=prefix, format=format.lower(), files=files,
                    gather_statistics_from_formula_file=gather_statistics_from_formula_file,
                    gather_statistics_from_json_file=gather_statistics_from_json_file)
            except BenchmarkException as e:
                self._error(e)
            else:
                self.test_inputs.append(test_input)

    def _load_test_suites(self, test_suites_config: Dict) -> NoReturn:
        if test_suites_config is None:
            self._error("You must define at least one testSuite")
            return

        for test_suite_config in test_suites_config:
            # for error reporting
            with DictPoper(test_suite_config, self._logger, "[[testSuites]]",
                           copy.deepcopy(test_suite_config)) as poper:
                name, _ = poper.pop_key(variable="name",
                                        required=True,
                                        type_check=str)

                executable, _ = poper.pop_key(variable="executable",
                                              required=True,
                                              type_check=str)

                PATH, _ = poper.pop_key(variable="PATH",
                                        required=False,
                                        type_check=str)

                version, _ = poper.pop_key(variable="version",
                                           required=False,
                                           type_check=str)

                static_options, _ = poper.pop_key(variable="options",
                                                  default=[],
                                                  type_check=list,
                                                  required=False)

                capture_stdout, _ = poper.pop_key(variable="capture_stdout",
                                                  default=True,
                                                  type_check=bool,
                                                  required=False)

                if poper.errors_occured:
                    continue

                try:
                    test_suite = TestSuite(name=name, PATH=PATH, version=version, executable=executable,
                                           options=[option.strip() for option in static_options],
                                           test_inputs=self.test_inputs, capture_stdout=capture_stdout)
                    self._load_test_runs(test_suite_config, test_suite)
                except BenchmarkException as e:
                    self._error(e)
                else:
                    self.test_suites.append(test_suite)

    def _load_test_runs(self, config: Dict, test_suite: TestSuite) -> NoReturn:
        test_runs_config = config.pop("testRuns", None)
        if test_runs_config is None:
            self._error("You must define at least one testCase")
            return

        for test_case_config in test_runs_config:
            with DictPoper(test_case_config, self._logger, "[[testSuites.testRuns]]",
                           copy.deepcopy(test_case_config)) as poper:
                name, _ = poper.pop_key(variable="name",
                                        required=True,
                                        type_check=str)

                input_as_last_arg, _ = poper.pop_key(variable="input_as_last_argument",
                                                     required=False,
                                                     type_check=bool)

                input_after_option, _ = poper.pop_key(variable="input_after_option",
                                                      required=False,
                                                      type_check=str)

                exclude, ok = poper.pop_key(variable="exclude",
                                            default=[],
                                            required=False,
                                            type_check=list)

                if ok:
                    for test_input_name in exclude:
                        if not any(test_input_name == test_input.name for test_input in test_suite.test_inputs):
                            self._error(f"exclude: there is no [[testInput]] named {test_input_name}")
                            poper.errors_occured = True

                include_only, ok = poper.pop_key(variable="include_only",
                                                 default=[],
                                                 required=False,
                                                 type_check=list)

                if ok:
                    for test_input_name in include_only:
                        if not any(test_input_name == test_input.name for test_input in test_suite.test_inputs):
                            self._error(
                                f"include_only: there is no [[testInput]] named {test_input_name} in {poper.log_context}")
                            poper.errors_occured = True

                format, ok = poper.pop_key(variable="format",
                                           required=True,
                                           type_check=str)

                # nested list
                options, _ = poper.pop_key(variable="options",
                                           required=True,
                                           type_check=list)

                if poper.errors_occured:
                    continue

            try:
                test_run = TestRun(name=name,
                                   format=format,
                                   input_after_option=input_after_option,
                                   input_as_last_argument=input_as_last_arg,
                                   exclude=exclude,
                                   include_only=include_only,
                                   options=options)
            except BenchmarkException as e:
                self._error(e)
                # self._logger.error(f"{e.args[0]} in {e.args[1:]}")
            else:
                test_suite.test_runs.append(test_run)

    def _error(self, message):
        self._load_errors_occured = True
        if isinstance(message, Exception):
            log = f"{message.args[0]}"
            if message.args[1:]:
                log = f"{log} in {' '.join(map(str, message.args[1:]))}"
            self._logger.error(log)
        else:
            self._logger.error(message)


if __name__ == "__main__":
    c = Config("../config.toml")
    c.load_config()
    pprint(c)
