"""evohomeasync provides an async client for the Resideo TCC API."""

from __future__ import annotations

import re
from datetime import datetime as dt
from typing import TYPE_CHECKING, Any, TypeVar

from .const import _DBG_DONT_OBFUSCATE, REGEX_EMAIL_ADDRESS

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import tzinfo

_T = TypeVar("_T")


def _convert_keys(data: _T, fnc: Callable[[str], str]) -> _T:
    """Recursively convert all dict keys as per some function.

    For example, converts all keys to snake_case, or CamelCase, etc.
    Used after retrieving (or before sending) JSON via the vendor API.
    """

    def recurse(data_: Any) -> Any:
        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        if not isinstance(data_, dict):
            return data_

        return {fnc(k): recurse(v) for k, v in data_.items()}

    return recurse(data)  # type:ignore[no-any-return]


def _convert_vals(data: _T, fnc: Callable[[str], str]) -> _T:
    """Recursively convert all string values as per some function.

    For example, converts all isoformat string values to TZ-aware format.
    Used after retrieving (or before sending) JSON via the vendor API.
    """

    def recurse(data_: Any) -> Any:
        if isinstance(data_, dict):
            return {fnc(k): recurse(v) for k, v in data_.items()}

        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        if isinstance(data_, str):
            return fnc(data_)

        return data_

    return recurse(data)  # type:ignore[no-any-return]


def as_local_time(dtm: dt | str, tzinfo: tzinfo) -> dt:
    """Convert a datetime into a aware datetime in the given TZ.

    If the datetime is naive, assume it is in the same timezone as tzinfo.
    """

    if isinstance(dtm, str):
        dtm = dt.fromisoformat(dtm)

    return dtm.replace(tzinfo=tzinfo) if dtm.tzinfo is None else dtm.astimezone(tzinfo)


_STEP_1 = re.compile(r"(.)([A-Z][a-z]+)")
_STEP_2 = re.compile(r"([a-z0-9])([A-Z])")


def camel_to_pascal(s: str) -> str:
    """Return a string convert (from camelCase) to PascalCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    return s[:1].upper() + s[1:]


def camel_to_snake(s: str) -> str:
    """Return a string converted (from camelCase) to snake_case."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    return _STEP_2.sub(r"\1_\2", _STEP_1.sub(r"\1_\2", s)).lower()


def snake_to_camel(s: str) -> str:
    """Return a string converted (from snake_case) to camelCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def noop(s: _T) -> _T:
    """Return a value (usually a string) unconverted."""
    return s


def convert_keys_to_camel_case(data: _T) -> _T:
    """Recursively convert all dict keys from snake_case to camelCase.

    Used before sending JSON to the vendor API.
    """
    return _convert_keys(data, snake_to_camel)


def convert_keys_to_snake_case(data: _T) -> _T:
    """Recursively convert all dict keys from camelCase to snake_case.

    Used after retrieving JSON from the vendor API.
    """
    return _convert_keys(data, camel_to_snake)


def convert_naive_dtm_strs_to_aware(data: _T, tzinfo: tzinfo) -> _T:
    """Recursively convert TZ-naive datetime strings to TZ-aware.

    Does not convert TZ-aware strings, even if they're from a different TZ.
    Used after retrieving JSON from the vendor API.
    """

    def recurse(data_: Any) -> Any:  # noqa: PLR0911
        if isinstance(data_, dict):
            return {k: recurse(v) for k, v in data_.items()}

        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        if not isinstance(data_, str):
            return data_

        try:
            d = dt.fromisoformat(data_)
        except ValueError:
            return data_

        if d.tzinfo is None:  # e.g. 2023-11-30T22:10:00
            return d.replace(tzinfo=tzinfo).isoformat()

        if data_.endswith("Z"):  # e.g. 2023-11-30T22:10:00Z
            return d.astimezone(tzinfo).isoformat()

        return data_  # e.g. 2023-11-30T22:10:00+00:00

    return recurse(data)  # type:ignore[no-any-return]


def obfuscate(value: bool | int | str) -> bool | int | str | None:
    """Obfuscate a value (usually to protect secrets during logging)."""

    if _DBG_DONT_OBFUSCATE:
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return 0
    if not isinstance(value, str):
        raise TypeError(f"obfuscate() expects bool | int | str, got {type(value)}")
    if REGEX_EMAIL_ADDRESS.match(value):
        return "******@obfuscated.com"
    return "********"


_KEYS_TO_OBSCURE = (  # also keys with 'name' in them
    "streetAddress",
    "city",
    "postcode",
    "zipcode",
    "telephone",
    "securityQuestion1",
    "securityQuestion2",
    "securityQuestion3",
    "mac",
    "crc",
)


def obscure_secrets(data: _T) -> _T:
    """Recursively obsfucate all dict/list values that might be secrets.

    Used when logging JSON received from the vendor API.
    """

    def _obfuscate(key: str, val: Any) -> Any:
        if not isinstance(val, str):
            return obfuscate(val)
        if REGEX_EMAIL_ADDRESS.match(val):
            return "nobody@nowhere.com"
        if "name" in key:
            return val[:2].ljust(len(val), "*")
        return "".join("*" if char != " " else " " for char in val)

    def should_obfuscate(key: Any) -> bool:
        return isinstance(key, str) and ("name" in key or key in _KEYS_TO_OBSCURE)

    def recurse(data_: Any) -> Any:
        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        if not isinstance(data_, dict):
            return data_

        return {
            k: _obfuscate(k, v) if should_obfuscate(k) else recurse(v)
            for k, v in data_.items()
        }

    return data if _DBG_DONT_OBFUSCATE else recurse(data)  # type:ignore[no-any-return]
