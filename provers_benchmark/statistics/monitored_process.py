import subprocess
import time

import psutil

from provers_benchmark.statistics.stats import ExecutionStatistics


class MonitoredProcess(subprocess.Popen):
    """Start process that can be monitored by periodic calling poll() in active loop
    Note that:
    poll() must be called at least once to get proper statistics
    short running process can exit before poll method was executed
    use with context manager to auto stop execution time
    """

    def __init__(self, *args, **kwargs):
        self.exec_stats = ExecutionStatistics()
        super().__init__(*args, **kwargs)
        self._start = time.perf_counter()
        self.proc = psutil.Process(self.pid)
        self.poll()

    def poll(self):
        if super().poll() is not None:
            return super().poll()

        # can not do it in __exit__, because process no longer not exists there
        self.exec_stats.update(self.proc)

        return None

    def stop(self):
        """If not used with contex manager, stop counting execution time"""
        self.__exit__(None, None, None)

    def get_statistics(self) -> ExecutionStatistics:
        """Return gathered statistics"""
        return self.exec_stats

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.exec_stats.execution_time = time.perf_counter() - self._start
        self.exec_stats.returncode = self.returncode
