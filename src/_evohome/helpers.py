"""evohomeasync provides an async client for the Resideo TCC API."""

from __future__ import annotations

import re
from datetime import UTC, datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final, overload

from .const import _DBG_DONT_REDACT_SECRETS, REGEX_EMAIL_ADDRESS
from .exceptions import BadApiRequestError

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import tzinfo


# Vendor API datetime format (ISO 8601, UTC, no fractional seconds)
TCC_DTM_STRFTIME: Final = "%Y-%m-%dT%H:%M:%SZ"
# _TCC_DTM_REGEX: Final = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z"

# However, the 'since' datetime used for Faults is naive, and has milliseconds
# NOTE: "2023-05-04T18:47:36.7727046" (7, not 6 digits) seen with gateway fault
# _TCC_SINCE_DTM: Final = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{1,}$"


_REDACTED_EMAIL_ADDRESS = "no-reply@redacted.xxx"
_REDACTED_STRING = "********"

_REDACTED_KEYS = (  # also keys with 'name' in them
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


# These are used after retrieving (or before sending) JSON via the vendor API.


def _recurse_keys[T](data: T, fnc: Callable[[str], str]) -> T:
    """Recursively convert JSON keys as per some function.

    For example, converts all string keys to snake_case, or CamelCase, etc.
    """

    def recurse(data_: Any) -> Any:
        if isinstance(data_, dict):
            return {fnc(k): recurse(v) for k, v in data_.items()}

        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        return data_

    return recurse(data)  # type:ignore[no-any-return]


def _recurse_str_vals[T](data: T, fnc: Callable[[str], str]) -> T:
    """Recursively convert JSON string values as per some function.

    For example, converts all isoformat string values to TZ-aware format.
    """

    def recurse(data_: Any) -> Any:
        if isinstance(data_, dict):
            return {k: recurse(v) for k, v in data_.items()}

        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        if not isinstance(data_, str):
            return data_

        return fnc(data_)

    return recurse(data)  # type:ignore[no-any-return]


def _recurse_enum_vals[T](data: T, fnc: Callable[[str], str]) -> T:
    """Recursively convert JSON StrEnum values as per some function."""
    return _recurse_str_vals(data, lambda s: fnc(s) if isinstance(s, StrEnum) else s)


def _recurse_dtm_vals[T](data: T, fnc: Callable[[dt], dt | str]) -> T:
    """Recursively convert JSON datetime objects as per some function.

    For example, converts all datetimes to local TZ.
    """

    def recurse(data_: Any) -> Any:
        if isinstance(data_, dict):
            return {k: recurse(v) for k, v in data_.items()}

        if isinstance(data_, list):
            return [recurse(i) for i in data_]

        if not isinstance(data_, dt):
            return data_

        return fnc(data_)

    return recurse(data)  # type:ignore[no-any-return]


def as_utc_str(dtm: dt) -> str:
    """Return a vendor (ISO 8601, UTC) datetime string from an aware datetime.

    The datetime is converted to UTC before formatting, so the trailing 'Z' in
    TCC_DTM_STRFTIME is truthful (an aware non-UTC datetime is sent as the correct UTC
    instant, not its wall-clock fields relabelled as UTC). A naive datetime is rejected.
    """

    if dtm.tzinfo is None:  # else astimezone() would assume the local TZ
        raise BadApiRequestError(f"Datetime must be TZ-aware (not naive): {dtm!r}")

    return dtm.astimezone(UTC).strftime(TCC_DTM_STRFTIME)


def as_local_time(dtm: dt | str, tzinfo: tzinfo) -> dt:
    """Convert a datetime into a aware datetime in the given TZ.

    If the datetime is naive, assume it is in the same timezone as tzinfo.
    """

    if isinstance(dtm, str):
        dtm = dt.fromisoformat(dtm)

    return dtm.replace(tzinfo=tzinfo) if dtm.tzinfo is None else dtm.astimezone(tzinfo)


def as_aware_dtm(dtm: dt | str) -> dt:
    """Return an aware datetime from a datetime or an ISO 8601 string.

    Strings are parsed via fromisoformat; a naive datetime is rejected, as its UTC
    instant would otherwise be ambiguous. Used to normalise a user-supplied 'until'
    before it is sent to the vendor API.
    """

    if isinstance(dtm, str):
        try:
            dtm = dt.fromisoformat(dtm)
        except ValueError as err:
            raise BadApiRequestError(f"Invalid datetime string: {dtm!r}") from err

    if dtm.tzinfo is None:
        raise BadApiRequestError(f"Datetime must be TZ-aware (not naive): {dtm!r}")

    return dtm


# These are used after retrieving (or before sending) JSON via the vendor API.


def convert_dtms_to_utc_str[T](data: T) -> T:
    """Recursively convert JSON datetime objects to ISO 8601 UTC strings."""
    return _recurse_dtm_vals(data, as_utc_str)


def convert_dtm_to_local_aware[T](data: T, tzinfo: tzinfo) -> T:
    """Recursively convert all datetimes to TZ-aware datetimes in the given TZ."""
    return _recurse_dtm_vals(data, lambda d: as_local_time(d, tzinfo))


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


pascal_to_snake = camel_to_snake  # PascalCase is a subset of camelCase


def snake_to_camel(s: str) -> str:
    """Return a string converted (from snake_case) to camelCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    components = s.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


def snake_to_pascal(s: str) -> str:
    """Return a string converted (from snake_case) to PascalCase."""
    if " " in s:
        raise ValueError("Input string should not contain spaces")
    return camel_to_pascal(snake_to_camel(s))


def noop[T](s: T) -> T:
    """Return a value (usually a string) unconverted."""
    return s


def convert_keys_to_camel_case[T](data: T) -> T:
    """Recursively convert all dict keys from snake_case to camelCase."""
    return _recurse_keys(data, snake_to_camel)


def convert_keys_to_snake_case[T](data: T) -> T:
    """Recursively convert all dict keys from camelCase to snake_case."""
    return _recurse_keys(data, camel_to_snake)


def convert_str_enums_to_pascal_case[T](data: T) -> T:
    """Recursively convert all StrEnum values from snake_case to PascalCase.

    Used before sending JSON to the vendor API. Only StrEnum members are converted;
    plain strings (names, datetimes, etc.) are left unchanged.
    """
    return _recurse_enum_vals(data, snake_to_pascal)


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


def _should_redact(key: str) -> bool:
    """Return True if a dict key indicates its value may be a secret."""
    # unfortunately, also redacts 'displayName' (is under 'timeZone')
    return "name" in key.lower() or key.lower() in _REDACTED_KEYS


def redact_secrets[T](data: T) -> T:
    """Recursively redact all dict/list values that might be secrets.

    Used when logging JSON received from the vendor API.
    """

    def _redact(key: str, val: Any) -> Any:
        """Redact a value under a sensitive key."""
        if not isinstance(val, str):
            return redact(val)
        if REGEX_EMAIL_ADDRESS.match(val):
            return _REDACTED_EMAIL_ADDRESS
        if "name" in key.lower():
            return val[:2].ljust(len(val), "*")
        return "".join("*" if char != " " else " " for char in val)

    def recurse(data_: Any) -> Any:
        if isinstance(data_, list):  # or Sequence?
            return [recurse(i) for i in data_]

        if isinstance(data_, tuple):
            return tuple(recurse(i) for i in data_)

        if not isinstance(data_, dict):  # Mapping?
            return data_

        return {
            k: _redact(k, v) if _should_redact(k) else recurse(v)
            for k, v in data_.items()
        }

    return data if _DBG_DONT_REDACT_SECRETS else recurse(data)
