import os
import subprocess
from typing import List, Union

from src.stats import MonitoredProcess


def execute(command: List[str],
            stdin: Union[str, int] = subprocess.DEVNULL,
            stdout: Union[str, int] = subprocess.DEVNULL,
            stderr: Union[str, int] = subprocess.DEVNULL,
            PATH: str = None,
            monitored: bool = False,
            *args, **kwargs) -> Union[subprocess.Popen, MonitoredProcess]:
    if isinstance(stdin, str):
        stdin = open(stdin, 'r')
    if isinstance(stdout, str):
        stdout = open(stdout, 'w')
    if isinstance(stderr, str):
        stderr = open(stderr, 'w')

    env = os.environ
    if PATH is not None:
        env["PATH"] = PATH + ":" + env["PATH"]

    if monitored:
        return MonitoredProcess(command,
                                stdin=stdin,
                                stdout=stdout,
                                stderr=stderr,
                                env=env,
                                *args,
                                **kwargs)
    else:
        return subprocess.Popen(command,
                                stdin=stdin,
                                stdout=stdout,
                                stderr=stderr,
                                env=env,
                                *args,
                                **kwargs)
