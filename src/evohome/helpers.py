#!/usr/bin/env python3
"""evohomeasync provides an async client for the Resideo TCC API."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, TypeVar

from .const import _DBG_DONT_OBFUSCATE, REGEX_EMAIL_ADDRESS

if TYPE_CHECKING:
    from collections.abc import Callable

_T = TypeVar("_T")


def obfuscate(value: bool | int | str) -> bool | int | str | None:
    if _DBG_DONT_OBFUSCATE:
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return 0
    if not isinstance(value, str):
        raise TypeError(f"obfuscate() expects bool | int | str, got {type(value)}")
    if REGEX_EMAIL_ADDRESS.match(value):
        return "nobody@nowhere.com"
    return "********"


def camel_to_pascal(s: str) -> str:
    """Convert a camelCase string to PascalCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    return s[:1].upper() + s[1:]


_STEP_1 = re.compile(r"(.)([A-Z][a-z]+)")
_STEP_2 = re.compile(r"([a-z0-9])([A-Z])")


def camel_to_snake(s: str) -> str:
    """Return a string converted from camelCase to snake_case."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    return _STEP_2.sub(r"\1_\2", _STEP_1.sub(r"\1_\2", s)).lower()


# assert camel_to_snake("camel2_camel2_case") == "camel2_camel2_case"
# assert camel_to_snake("getHTTPResponseCode") == "get_http_response_code"
# assert camel_to_snake("HTTPResponseCodeXYZ") == "http_response_code_xyz"


def snake_to_camel(s: str) -> str:
    """Return a string converted from snake_case to camelCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def noop(s: str) -> str:
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
