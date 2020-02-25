"""see http://eyalarubas.com/python-subproc-nonblock.html"""
from queue import Queue, Empty
from threading import Thread

from typing import IO, NoReturn


class NonBlockingStreamReader:

    def __init__(self, stream):
        """
        stream: the stream to read from.
                Usually a process' stdout or stderr.
        """

        self._s = stream
        self._q = Queue()

        def _populate_queue(stream: IO, queue: Queue) -> NoReturn:
            """
            Collect lines from 'stream' and put them in 'quque'.
            """

            while True:
                line = stream.readline()
                if line:
                    queue.put(line)
                else:
                    # raise error?
                    return

        self._t = Thread(target=_populate_queue,
                         args=(self._s, self._q))
        self._t.daemon = True
        self._t.start()  # start collecting lines from the stream

    def readline(self, timeout=None) -> str:
        try:
            return self._q.get(block=timeout is not None,
                               timeout=timeout)
        except Empty:
            return ''

    def readall(self):
        while not self._q.empty():
            yield self._q.get_nowait()
