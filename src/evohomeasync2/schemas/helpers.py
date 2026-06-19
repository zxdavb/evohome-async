"""Helper utilities for the vendor's TCC v2 API."""

from __future__ import annotations

from datetime import datetime as dt
from enum import StrEnum
from typing import TYPE_CHECKING

import voluptuous as vol

from _evohome.helpers import camel_to_snake

if TYPE_CHECKING:
    from collections.abc import Callable


# The casing convention a schema factory should produce, and the enum-field
# validator that switches between vendor and pythonic output.


class Case(StrEnum):
    """Selects the casing convention a schema factory should produce."""

    VENDOR = "vendor"  # camelCase keys, PascalCase enum strings (validate only)
    PYTHONIC = "pythonic"  # snake_case keys, coerced to user-facing enum members


def factory_enum(
    case: Case,
    tcc_cls: type[StrEnum],
) -> vol.In | Callable[[object], StrEnum]:
    """Return a validator for an enum field, per the casing convention.

    For Case.VENDOR, validates the value is a member of the vendor (Tcc*) enum.

    For Case.PYTHONIC, coerces the vendor value (e.g. "Auto") to the matching
    user-facing enum member (e.g. SystemMode.AUTO).

    An unexpected value raises ValueError, which voluptuous reports as vol.Invalid.
    """

    if case is Case.VENDOR:
        return vol.In(tcc_cls)

    # the user-facing enums live in the (vendor-agnostic) parent package; import
    # them lazily as they, in turn, derive their values from these Tcc* enums
    from evohomeasync2 import const  # noqa: PLC0415

    evo_cls: type[StrEnum] = getattr(const, tcc_cls.__name__.removeprefix("Tcc"))

    def coerce_enum(value: object) -> StrEnum:
        return evo_cls(camel_to_snake(str(value)))

    return coerce_enum


def factory_datetime(case: Case) -> Callable[[object], dt | str]:
    """Return a validator for a datetime field, per the casing convention.

    For Case.VENDOR, validates the value is an ISO 8601 string (and keeps it).

    For Case.PYTHONIC, coerces it to a datetime (a 'Z' suffix gives an aware UTC
    datetime; a naive string gives a naive datetime). The coercer is idempotent - a
    datetime passes through unchanged - so re-validating already-coerced data works.

    A value that cannot be parsed raises vol.Invalid.
    """

    if case is Case.VENDOR:

        def validate_dtm(value: object) -> str:
            if not isinstance(value, str):
                raise vol.Invalid(f"expected an ISO 8601 string, got {value!r}")
            try:
                dt.fromisoformat(value)  # validate only; keep the original string
            except ValueError as err:
                raise vol.Invalid(f"invalid datetime: {value!r}") from err
            return value

        return validate_dtm

    def coerce_dtm(value: object) -> dt:
        if isinstance(value, dt):  # idempotent (e.g. on re-validation)
            return value
        if isinstance(value, str):
            return dt.fromisoformat(value)
        raise vol.Invalid(f"expected a datetime or ISO 8601 string, got {value!r}")

    return coerce_dtm
