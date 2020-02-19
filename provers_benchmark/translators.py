import os
import subprocess
from dataclasses import dataclass, field, InitVar
from typing import List, Optional

from provers_benchmark.errors import BenchmarkException
from provers_benchmark.log import get_logger

logger = get_logger()


@dataclass
class Translator:
    """Translate text to different syntax by calling executable
    by default input file is piped to stdin, stdout is piped to output file
    if input_as_last_argument is True, input_filename will be last arguments
    input_as_last_argument and input_after_option are mutually exclusive
    """
    from_format: str
    to_format: str
    executable: str
    extension: str = None
    cwd: InitVar[str] = os.getcwd()
    options: List[str] = field(default_factory=list)
    input_after_option: str = None
    input_as_last_argument: bool = False
    output_after_option: str = None
    PATH: str = None

    def __post_init__(self, cwd):
        if self.PATH is not None:
            self.PATH = os.path.abspath(os.path.join(cwd, self.PATH))

        if not self.extension.startswith('.'):
            self.extension = f".{self.extension}"

        if not os.path.isdir(self.PATH):
            raise BenchmarkException(f"PATH '{self.PATH}' is not a directory", self)

        if self.input_after_option and self.input_as_last_argument:
            raise BenchmarkException("Options input_after_option and input_as_last_argument are mutually exclusive",
                                     self)

    def translate(self, input_filename: str, output_filename: str) -> Optional[subprocess.Popen]:
        command = self.get_command(input_filename, output_filename)
        env = os.environ
        if self.PATH:
            env['PATH'] = self.PATH + ':' + env['PATH']
        return subprocess.Popen(command, stdin=open(input_filename, 'r'), stdout=open(output_filename, 'w'), env=env)

    def get_command(self, input_filename: str, output_filename: str) -> List[str]:
        """Command is composed as follows:
        executable [options] [input_after_option input_filename] [output_output_after_option out_filename]
        :return: list representing executable and options
        """
        command = [self.executable]
        command.extend(self.options)
        if self.input_after_option:
            command.append(self.input_after_option)
            command.append(input_filename)

        if self.output_after_option:
            command.append(self.output_after_option)
            command.append(output_filename)

        if self.input_as_last_argument:
            command.append(input_filename)
        return command


if __name__ == '__main__':
    translator = Translator(from_format="TPTP",
                            to_format="LADR",
                            executable="tptp_to_ladr",
                            PATH="../../provers/LADR-2009-11A/bin")
    translator.translate(input_filename="../../TPTP-v7.2.0/example.p", output_filename="example_converted.in")
