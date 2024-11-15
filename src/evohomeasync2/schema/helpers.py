#!/usr/bin/env python3
"""evohomeasync schema - shared helpers."""

from __future__ import annotations

import re
from typing import TypeVar

from .const import REGEX_EMAIL_ADDRESS

_T = TypeVar("_T")


# all _DBG_* flags should be False for published code
_DBG_DONT_OBSFUCATE = False  # default is to obsfucate JSON in debug output


def obfuscate(value: bool | int | str) -> bool | int | str | None:
    if _DBG_DONT_OBSFUCATE:
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return 0
    if not isinstance(value, str):
        raise TypeError(f"obfuscate() expects bool | int | str, got {type(value)}")
    if re.match(REGEX_EMAIL_ADDRESS, value):
        return "nobody@nowhere.com"
    return "********"


def camel_case(s: str) -> str:
    """Convert a PascalCase string to camelCase."""
    return s[:1].lower() + s[1:]


def pascal_case(s: str) -> str:
    """Convert a camelCase string to PascalCase."""
    return s[:1].upper() + s[1:]


def camel_to_snake(s: str) -> str:
    """Return a string converted from camelCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(s: str) -> str:
    """Return a string converted from snake_case to camelCase."""
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def _do_nothing(s: str) -> str:
    """Return a string unconverted."""
    return s


def convert_keys_to_snake_case(data: _T) -> _T:
    """Convert all keys in a dictionary to snake_case.

    Used after retreiiving JSON data from the vendor API.
    """

    if isinstance(data, list):
        return [convert_keys_to_snake_case(item) for item in data]  # type: ignore[return-value]

    if not isinstance(data, dict):
        return data

    return {camel_to_snake(k): convert_keys_to_snake_case(v) for k, v in data.items()}  # type: ignore[return-value]


assert snake_to_camel("snakeToCamel") == "snakeToCamel"
assert camel_to_snake("snakeToCamel") == "snake_to_camel"
assert camel_to_snake("snake_to_camel") == "snake_to_camel"
assert snake_to_camel("snake_to_camel") == "snakeToCamel"
