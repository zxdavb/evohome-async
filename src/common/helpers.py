#!/usr/bin/env python3
"""evohomeasync provides an async client for the v0 Resideo TCC API."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import TypeVar

from .const import _DBG_DONT_OBSFUCATE, REGEX_EMAIL_ADDRESS

_T = TypeVar("_T")


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


def camel_to_pascal(s: str) -> str:
    """Convert a camelCase string to PascalCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    return s[:1].upper() + s[1:]


def camel_to_snake(s: str) -> str:
    """Return a string converted from camelCase to snake_case."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", s)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(s: str) -> str:
    """Return a string converted from snake_case to camelCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def do_nothing(s: str) -> str:
    """Return a string unconverted."""
    return s


def _convert_keys(data: _T, fnc: Callable[[str], str]) -> _T:
    """Convert all keys in a dictionary to snake_case.

    Used after retreiiving JSON data from the vendor API.
    """

    if isinstance(data, list):
        return [convert_keys_to_snake_case(item) for item in data]  # type: ignore[return-value]

    if not isinstance(data, dict):
        return data

    return {fnc(k): convert_keys_to_snake_case(v) for k, v in data.items()}  # type: ignore[return-value]


def convert_keys_to_camel_case(data: _T) -> _T:
    return _convert_keys(data, camel_to_snake)


def convert_keys_to_snake_case(data: _T) -> _T:
    return _convert_keys(data, camel_to_snake)
