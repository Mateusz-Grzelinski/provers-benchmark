from typing import Any, List, Dict


class BenchmarkException(Exception):
    pass


class BenchmarkConfigException(BenchmarkException):
    def __init__(self, *args: object, failing_keys: Dict[str, Any] = None) -> None:
        self.failing_keys = failing_keys if failing_keys is not None else {}
        super().__init__(*args)
