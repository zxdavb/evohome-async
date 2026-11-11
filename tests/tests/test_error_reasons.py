"""Test that each error raised (that is to have one) has a reason.

The reasons are public API (e.g. HA may map each one to its own translated message).
They are optional, so that the errors can still be raised with only a message, so mypy
will not catch the omission of one: these tests do.
"""

from __future__ import annotations

import ast
from functools import cache
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import _evohome
from _evohome import exceptions as exc
from _evohome.exceptions import (
    ClientStateErrorReason,
    RequestErrorReason,
    ResponseErrorReason,
)

if TYPE_CHECKING:
    from enum import StrEnum

_SRC = Path(_evohome.__file__).parent.parent  # incl. evohomeasync, evohomeasync2

# the errors that the library must raise with a reason
_REASONED = (exc.BadApiRequestError, exc.BadApiResponseError, exc.ClientStateError)

_ENUMS = (RequestErrorReason, ResponseErrorReason, ClientStateErrorReason)

_BY_NAME = {  # incl. the aliases of their previous names (e.g. InvalidModeRequestError)
    n: c
    for n, c in vars(exc).items()
    if isinstance(c, type) and issubclass(c, _REASONED)
}

# the names of the classes (and of their aliases, incl. those served by __getattr__)
_NAMES = set(_BY_NAME) | {"InvalidSystemModeError"}

# the errors that have a reason (attr)
_CLASSES = sorted(set(_BY_NAME.values()), key=lambda c: c.__name__)


@cache
def _modules() -> tuple[tuple[str, ast.Module], ...]:
    """Return the library's modules, as parsed (each with its path, for messages)."""
    return tuple(
        (str(p.relative_to(_SRC)), ast.parse(p.read_text(), filename=str(p)))
        for p in sorted(_SRC.rglob("*.py"))
    )


def test_raise_sites_have_a_reason() -> None:
    """Test every raise of an error that is to have a reason has one."""

    raises: list[str] = []
    missing: list[str] = []

    for path, module in _modules():
        for node in ast.walk(module):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            func = node.exc.func
            name = func.attr if isinstance(func, ast.Attribute) else ""
            name = func.id if isinstance(func, ast.Name) else name
            if name not in _NAMES:
                continue
            raises.append(site := f"{path}:{node.lineno}")
            if not any(k.arg == "reason" for k in node.exc.keywords):
                missing.append(site)

    assert raises, "no raise sites were found (has the source moved?)"
    assert not missing, f"raised without a reason: {missing}"


@pytest.mark.parametrize("enum", _ENUMS, ids=lambda e: e.__name__)
def test_reasons_are_all_used(
    enum: type[RequestErrorReason | ResponseErrorReason | ClientStateErrorReason],
) -> None:
    """Test every reason is used by the library (i.e. none is unreachable)."""

    used: set[str] = set()

    for _, module in _modules():
        for node in ast.walk(module):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == enum.__name__
            ):
                used.add(node.attr)

    assert used == set(enum.__members__)


def test_reasons_are_unique() -> None:
    """Test every reason's value is unique, across the enums (not just within each).

    A caller may map a reason's value to a message (e.g. as a translation key), and a
    StrEnum member equals its value, so a value in two enums would be ambiguous.
    """

    values = [r.value for e in _ENUMS for r in e.__members__.values()]  # incl. aliases
    duplicates = sorted({v for v in values if values.count(v) > 1})

    assert not duplicates, f"reasons that are not unique: {duplicates}"


def test_reasons_are_prefixed() -> None:
    """Test every reason's value is its name, prefixed as per its enum.

    That is: set_ (a request) or get_ (a response), as are the errors' names (e.g.
    InvalidSetModeError, InvalidGetConfigError), or cfg_ (the config/status data). The
    prefixes also keep the values of the enums apart (see above).
    """

    assert all(r.value == f"set_{r.name.lower()}" for r in RequestErrorReason)
    assert all(r.value == f"get_{r.name.lower()}" for r in ResponseErrorReason)
    assert all(r.value == f"cfg_{r.name.lower()}" for r in ClientStateErrorReason)


# the errors with only one reason, which is then their default (the others have none)
_DEFAULT_REASONS: dict[type[exc.EvohomeError], StrEnum] = {
    exc.InvalidGetConfigError: ResponseErrorReason.CONFIG_INVALID,
    exc.InvalidGetStatusError: ResponseErrorReason.STATUS_INVALID,
    exc.InvalidSetScheduleError: RequestErrorReason.SCHEDULE_INVALID,
}


@pytest.mark.parametrize("cls", _CLASSES, ids=lambda c: c.__name__)
def test_error_without_a_reason(
    cls: type[exc.BadApiRequestError | exc.BadApiResponseError | exc.ClientStateError],
) -> None:
    """Test each error can still be raised with only a message (as before reasons).

    Its reason is then its class's default, if it has one (else None).
    """

    err = cls("a message")  # e.g. as HA's tests do

    assert err.message == "a message"
    assert err.reason is _DEFAULT_REASONS.get(cls)
    assert err.details == {}


def test_error_with_a_reason() -> None:
    """Test a reason, if given, is used rather than the class's default."""

    err = exc.InvalidGetConfigError(
        "a message", reason=ResponseErrorReason.ACCOUNT_INVALID
    )

    assert err.reason is ResponseErrorReason.ACCOUNT_INVALID
