from __future__ import annotations
import os
from typing import Optional, List


def is_path_executable(fpath: str):
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def command_name(command: str):
    return command.split()[0]


def executable_name(command: str):
    return os.path.basename(command_name(command))


def which(program: str):
    fpath, fname = os.path.split(program)
    if fpath:
        if is_path_executable(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, program)
            if is_path_executable(exe_file):
                return exe_file
    return None


def build_command(command: str, input_file: Optional[str], input_mode: Optional[InputMode], output_file: Optional[str],
                  output_mode: Optional[OutputMode]) -> str:
    from provers_benchmark.config import InputMode, OutputMode, INPUT_PATH_TEMPLATE, OUTPUT_PATH_TEMPLATE, Translator
    if input_mode == InputMode.ARGUMENT:
        command = command.replace(INPUT_PATH_TEMPLATE, input_file)

    if output_mode == OutputMode.ARGUMENT:
        command = command.replace(OUTPUT_PATH_TEMPLATE, output_file)

    return command


def find_translator(from_format: str, to_format: str, available_translators: List[Translator]):
    for translator in available_translators:
        if translator.from_format == from_format and translator.to_format == to_format:
            return translator
