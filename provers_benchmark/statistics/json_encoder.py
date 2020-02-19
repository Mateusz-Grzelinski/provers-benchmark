import datetime
import json
from enum import Enum
from inspect import isclass


class ClassAsDictJSONEncoder(json.JSONEncoder):
    """This encoder can encode Enum and classes that inherit Serializable
    Usage json.dumps(variable, cls=SerializableJSONEncoder)
    """

    def default(self, o):
        if hasattr(o, '__dict__'):
            return self._as_plain_dict(o)
        if isinstance(o, Enum):
            return o.value
        return super().default(o)

    def _as_plain_dict(self, o):
        """Convert to dict that holds only basic types"""
        # todo ignore variables that start with _
        class_dict = o.__dict__.copy()
        for key, value in o.__dict__.items():
            if key.startswith('_') or key.startswith(self.__class__.__name__):
                class_dict.pop(key)
                continue
            # recursion is not efficies, but is is easy
            if isinstance(value, datetime.datetime):
                class_dict[key] = value.isoformat()
            elif isclass(value):
                class_dict[key] = self._as_plain_dict(value)
        return class_dict
