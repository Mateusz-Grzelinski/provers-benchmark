from typing import Any, List, Dict, Optional

import dacite

from provers_benchmark.parsers.parsers import get_all_output_parsers


class BenchmarkException(Exception):
    pass


class BenchmarkConfigException(BenchmarkException):
    def __init__(self, *args: object, field_paths: Dict[str, Any] = None) -> None:
        self.field_paths = field_paths if field_paths is not None else {}
        super().__init__(*args)

    def update_field_path(self, parent_key: str) -> None:
        old_fields = self.field_paths.copy()
        self.field_paths = {f'{parent_key}.{key}': value for key, value in old_fields.items()}

    @property
    def _get_fields_as_string(self) -> str:
        return ', '.join(f'{key}={val}' for key, val in self.field_paths.items())

    def __str__(self):
        message = super(BenchmarkConfigException, self).__str__()
        if not message.endswith(' '):
            message = f'{message} '
        return message + f'({self._get_fields_as_string})'


class DaciteArgumentValueError(dacite.DaciteFieldError):
    def __init__(self, available_values: List, current_value: Any, field_path: Optional[str] = None):
        super().__init__(field_path)
        self.current_value = current_value
        self.available_values = available_values

    def __str__(self):
        values = ', '.join(str(i) for i in self.available_values)
        return f'Wrong value for field {self.field_path}. Available values: [{values}] but is {self.current_value}'


class UnsupportedSolver(BenchmarkConfigException):
    def __init__(self, *args: object, field_paths: Dict[str, Any] = None, solver: str) -> None:
        super().__init__(*args, field_paths=field_paths)
        self.solver = solver

    def __str__(self):
        return f'solver {self.solver} is not supported in field {self.field_paths}. Use one of {get_all_output_parsers()} or add ' \
               f'it in provers_benchmark/parsers/output_parsers.py '
