"""evohomeasync provides an async client for the Resideo TCC API."""

from __future__ import annotations

import re
from datetime import datetime as dt
from typing import TYPE_CHECKING, Any, overload

from .const import _DBG_DONT_REDACT_SECRETS, REGEX_EMAIL_ADDRESS

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import tzinfo


REGEX_DATETIME = r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"

_REDACTED_EMAIL_ADDRESS = "no-reply@redacted.xxx"
_REDACTED_STRING = "********"


def _convert_keys[T](data: T, fnc: Callable[[str], str]) -> T:
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


def _convert_vals[T](data: T, fnc: Callable[[str], str]) -> T:
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


def noop[T](s: T) -> T:
    """Return a value (usually a string) unconverted."""
    return s


def convert_keys_to_camel_case[T](data: T) -> T:
    """Recursively convert all dict keys from snake_case to camelCase.

    Used before sending JSON to the vendor API.
    """
    return _convert_keys(data, snake_to_camel)


def convert_keys_to_snake_case[T](data: T) -> T:
    """Recursively convert all dict keys from camelCase to snake_case.

    Used after retrieving JSON from the vendor API.
    """
    return _convert_keys(data, camel_to_snake)


def convert_naive_dtm_strs_to_aware[T](data: T, tzinfo: tzinfo) -> T:
    """Recursively convert TZ-naive datetime strings to TZ-aware.

    Does not convert TZ-aware strings, even if they're from a different TZ.
    Used after retrieving JSON from the vendor API.
    """

    def recurse(data_: Any) -> Any:  # noqa: PLR0911
        if isinstance(data_, dict):
            return {k: recurse(v) for k, v in data_.items()}

        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        if not isinstance(data_, str) or not re.match(REGEX_DATETIME, data_):
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


@overload
def redact(value: bool) -> bool | None: ...  # type: ignore[overload-overlap] # noqa: FBT001
@overload
def redact(value: int) -> int: ...
@overload
def redact(value: str) -> str: ...


def redact(value: bool | int | str) -> bool | int | str | None:  # noqa: FBT001
    """Redact a value (usually to protect secrets when logging)."""

    if _DBG_DONT_REDACT_SECRETS:
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return 0
    if not isinstance(value, str):
        raise TypeError(f"redact() expects bool | int | str, got {type(value)}")
    if REGEX_EMAIL_ADDRESS.match(value):
        return _REDACTED_EMAIL_ADDRESS
    return _REDACTED_STRING


_KEYS_TO_OBSCURE = (  # also keys with 'name' in them
    "city",
    "crc",
    "mac",
    "macid",
    "postcode",
    "securityquestion1",
    "securityquestion2",
    "securityquestion3",
    "streetaddress",
    "telephone",
    "zipcode",
)


def obscure_secrets[T](data: T) -> T:
    """Recursively redact all dict/list values that might be secrets.

    Used when logging JSON received from the vendor API.
    """

    def _redact(key: str, val: Any) -> Any:
        if not isinstance(val, str):
            return redact(val)
        if REGEX_EMAIL_ADDRESS.match(val):
            return _REDACTED_EMAIL_ADDRESS
        if "name" in key.lower():
            return val[:2].ljust(len(val), "*")
        return "".join("*" if char != " " else " " for char in val)

    def should_redact(key: Any) -> bool:
        # unfortunately, also redacts 'displayName' (is under 'timeZone')
        return isinstance(key, str) and (
            "name" in key.lower() or key.lower() in _KEYS_TO_OBSCURE
        )

    def recurse(data_: Any) -> Any:
        if isinstance(data_, list):  # or Sequence?
            return [recurse(i) for i in data_]

        if isinstance(data_, tuple):
            return tuple(recurse(i) for i in data_)

        if not isinstance(data_, dict):  # Mapping?
            return data_

        return {
            k: _redact(k, v) if should_redact(k) else recurse(v)
            for k, v in data_.items()
        }

    return data if _DBG_DONT_REDACT_SECRETS else recurse(data)
