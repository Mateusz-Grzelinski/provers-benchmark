import copy
import glob
import logging
import os
from dataclasses import dataclass, field
from pprint import pprint
from typing import List, Dict, Type, NoReturn

import toml

from src import BenchmarkException, ConfigException
from src.test import TestCase, TestSuite
from src.testinput import TestInput
from src.translators import Translator

# todo remove this and make proper logger
logging.basicConfig(level=logging.DEBUG)


@dataclass
class DictPoper:
    def __init__(self, source: dict, logger: logging.Logger = logging, *args, **kwargs):
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
        check type of variable
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

        return value, ok

    @property
    def log_context(self):
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
    config_file: str = "config.toml"
    output_dir: str = "benchmark-output"
    log_file: str = "benchmark.log"
    test_suites: List[TestSuite] = field(default_factory=list)
    test_inputs: List[TestInput] = field(default_factory=list)

    _load_errors_occured: bool = False
    _logger: logging.Logger = logging.getLogger("Config")

    def __post_init__(self):
        self._logger.setLevel(logging.DEBUG)

    def load_config(self) -> NoReturn:
        """Load and verify config"""
        self._load_errors_occured = False
        if not os.path.isfile(self.config_file):
            self._error(f"Config file '{self.config_file}'' is not found/not a file")
            return

        self._logger.info(f"Reading {self.config_file}")
        with open(self.config_file) as source:
            benchmark_config = toml.load(self.config_file)

        with DictPoper(benchmark_config, self._logger, self.config_file) as poper:
            general_config, _ = poper.pop_key("general", required=True, type_check=dict)
            self._load_general(general_config)
            translators_config, _ = poper.pop_key("translators", required=True, type_check=list)
            self._load_translators(translators_config)
            test_inputs_config, _ = poper.pop_key("testInputs", required=True, type_check=list)
            self._load_test_inputs(test_inputs_config)
            test_suites_config, _ = poper.pop_key("testSuites", required=True, type_check=list)
            self._load_test_suites(test_suites_config)

            if poper.errors_occured or self._load_errors_occured:
                self.test_inputs.clear()
                TestInput.translators.clear()
                self.test_suites.clear()
                raise ConfigException("Errors occured in config. See log warnings and errors")
        self._logger.info("Config parsed successfully")

    def _load_general(self, general_config: Dict) -> NoReturn:
        with DictPoper(general_config, self._logger, "[general]", copy.deepcopy(general_config)) as poper:
            self.log_file, _ = poper.pop_key(variable="log_file",
                                             default=self.log_file,
                                             required=False,
                                             type_check=str)

            self.output_dir, _ = poper.pop_key(variable="output_dir",
                                               default=self.output_dir,
                                               required=False,
                                               type_check=str)
            # todo check is is writeable (should be dir or file?

    def _load_translators(self, translators_config: List) -> NoReturn:
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

                path, _ = poper.pop_key(variable="PATH",
                                        default=None,
                                        type_check=str)

                if poper.errors_occured:
                    continue
            try:
                translator = Translator(from_format=from_format,
                                        to_format=to_format,
                                        executable=executable,
                                        options=options,
                                        input_as_last_argument=input_as_last_argument,
                                        input_after_option=input_after_option,
                                        output_after_option=output_after_option,
                                        PATH=path)
                translator.verify()
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

                files = []
                for pattern in patterns:
                    wildcard = os.path.join(path, pattern)
                    resolved_paths = glob.glob(wildcard, recursive=True)
                    resolved_files = [resolved_path for resolved_path in resolved_paths if
                                      os.path.isfile(resolved_path)]
                    if resolved_files:
                        files.extend(resolved_files)
                        self._logger.debug(f"{wildcard} matched files: {resolved_files}")
                    else:
                        self._logger.warning(f"pattern {wildcard} did not match any file")

                if not files:
                    self._error(f"no file defined for testInput")
                    continue

                if poper.errors_occured:
                    continue

            try:
                test_input = TestInput(name=name,
                                       path=path,
                                       format=format,
                                       files=files)
                test_input.verify()
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

                if poper.errors_occured:
                    continue

                try:
                    test_suite = TestSuite(name=name,
                                           PATH=PATH,
                                           version=version,
                                           executable=executable,
                                           options=static_options,
                                           test_inputs=self.test_inputs)
                    self._load_test_cases(test_suite_config, test_suite)
                    test_suite.verify()
                except BenchmarkException as e:
                    self._error(e)
                else:
                    self.test_suites.append(test_suite)

    def _load_test_cases(self, config: Dict, test_suite: TestSuite) -> NoReturn:
        test_cases_config = config.pop("testCases", None)
        if test_cases_config is None:
            self._error("You must define at least one testCase")
            return

        for test_case_config in test_cases_config:
            with DictPoper(test_case_config, self._logger, "[[testSuites.testCases]]",
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
                            self._error(f"exclude: there is no testInput called {test_input_name}")
                            poper.errors_occured = True

                include_only, ok = poper.pop_key(variable="include_only",
                                                 default=[],
                                                 required=False,
                                                 type_check=list)

                if ok:
                    for test_input_name in include_only:
                        if not any(test_input_name == test_input.name for test_input in test_suite.test_inputs):
                            self._error(
                                f"include_only: there is no testInput called {test_input_name} in {poper.log_context}")
                            poper.errors_occured = True

                format, ok = poper.pop_key(variable="format",
                                           required=True,
                                           type_check=str)

                # note: TestInput is assumed to be tptp
                # todo support chaining translators
                if ok and not any(translator.to_format == format for translator in TestInput.translators):
                    self._error(f"format {format} is not achievable with defined translators: {TestInput.translators}")

                # nested list
                options, _ = poper.pop_key(variable="options",
                                           required=True,
                                           type_check=list)

                if poper.errors_occured:
                    continue

            try:
                test_case = TestCase(name=name,
                                     format=format,
                                     input_after_option=input_after_option,
                                     input_as_last_argument=input_as_last_arg,
                                     exclude=exclude,
                                     include_only=include_only,
                                     options=options)
                test_case.verify(test_suite)
            except BenchmarkException as e:
                self._error(e)
                # self._logger.error(f"{e.args[0]} in {e.args[1:]}")
            else:
                test_suite.test_cases.append(test_case)

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
