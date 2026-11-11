"""Test that each error raised has the right reason.

The reasons are public API (e.g. HA may map each one to its own translated message).
They are optional, so that the errors can still be raised with only a message, so mypy
will not catch the omission of one: these tests do.

An ApiCallFailedError (or a subclass) is raised with a reason only if it is not the
class's default (e.g. not RATE_LIMITED, for an ApiRateLimitExceededError); every other
error is always raised with a reason, even where it is the default.
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
    ApiCallErrorReason,
    ClientStateErrorReason,
    EvohomeErrorReason,
    RequestErrorReason,
    ResponseErrorReason,
)

if TYPE_CHECKING:
    from enum import StrEnum

_SRC = Path(_evohome.__file__).parent.parent  # incl. evohomeasync, evohomeasync2

# the errors that the library must raise with a reason
_REASONED = (exc.EvohomeError,)  # i.e. every error

_ENUMS = (
    EvohomeErrorReason,
    ApiCallErrorReason,
    RequestErrorReason,
    ResponseErrorReason,
    ClientStateErrorReason,
)

_BY_NAME = {  # incl. the aliases of their previous names (e.g. InvalidModeRequestError)
    n: c
    for n, c in vars(exc).items()
    if isinstance(c, type) and issubclass(c, _REASONED)
}

# the names of the classes (and of their aliases, incl. those served by __getattr__)
_NAMES = set(_BY_NAME) | {"ApiRequestFailedError", "InvalidSystemModeError"}

# the errors that are raised with a reason only if it is not their default
_API_CALL_NAMES = {
    n for n, c in _BY_NAME.items() if issubclass(c, exc.ApiCallFailedError)
} | {"ApiRequestFailedError"}

# the errors that have a reason (attr)
_CLASSES = sorted(set(_BY_NAME.values()), key=lambda c: c.__name__)


@cache
def _modules() -> tuple[tuple[str, ast.Module], ...]:
    """Return the library's modules, as parsed (each with its path, for messages)."""
    return tuple(
        (str(p.relative_to(_SRC)), ast.parse(p.read_text(), filename=str(p)))
        for p in sorted(_SRC.rglob("*.py"))
    )


def _name(call: ast.Call) -> str:
    """Return the name of what is called (e.g. "InvalidSetModeError")."""

    func = call.func
    if isinstance(func, ast.Attribute):  # e.g. exc.InvalidSetModeError(...)
        return func.attr
    return func.id if isinstance(func, ast.Name) else ""


def _reason(call: ast.Call) -> ast.expr | None:
    """Return the reason that is passed (if any)."""
    return next((k.value for k in call.keywords if k.arg == "reason"), None)


def test_raise_sites_have_a_reason() -> None:
    """Test every raise of an error has a reason (other than an ApiCallFailedError)."""

    raises: list[str] = []
    missing: list[str] = []

    for path, module in _modules():
        for node in ast.walk(module):
            if not isinstance(node, ast.Raise) or not isinstance(node.exc, ast.Call):
                continue
            if (name := _name(node.exc)) not in _NAMES or name in _API_CALL_NAMES:
                continue
            raises.append(site := f"{path}:{node.lineno}")
            if _reason(node.exc) is None:
                missing.append(site)

    assert raises, "no raise sites were found (has the source moved?)"
    assert not missing, f"raised without a reason: {missing}"


def test_api_call_errors_omit_their_default() -> None:
    """Test no ApiCallFailedError is created with its class's default reason.

    Every call is checked (not only raises), as some are created to be raised later.
    """

    calls: list[str] = []
    defaults: list[str] = []

    for path, module in _modules():
        for node in ast.walk(module):
            if not isinstance(node, ast.Call) or _name(node) not in _API_CALL_NAMES:
                continue
            calls.append(site := f"{path}:{node.lineno}")

            reason = _reason(node)
            if (  # e.g. reason=ApiCallErrorReason.RATE_LIMITED
                isinstance(reason, ast.Attribute)
                and isinstance(reason.value, ast.Name)
                and reason.value.id == ApiCallErrorReason.__name__
            ):
                cls = _BY_NAME.get(_name(node), exc.ApiCallFailedError)
                if ApiCallErrorReason[reason.attr] is cls._default_reason:
                    defaults.append(site)

    assert calls, "no calls were found (has the source moved?)"
    assert not defaults, f"created with its default reason: {defaults}"


@pytest.mark.parametrize("enum", _ENUMS, ids=lambda e: e.__name__)
def test_reasons_are_all_used(
    enum: type[
        EvohomeErrorReason
        | ApiCallErrorReason
        | RequestErrorReason
        | ResponseErrorReason
        | ClientStateErrorReason
    ],
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
    InvalidSetModeError, InvalidGetConfigError), cfg_ (the config/status data), api_
    (the call itself, e.g. a 429 or no connection), or evo_ (only the default of a bare
    EvohomeError). The prefixes also keep the values of the enums apart (see above).
    """

    assert all(r.value == f"set_{r.name.lower()}" for r in RequestErrorReason)
    assert all(r.value == f"get_{r.name.lower()}" for r in ResponseErrorReason)
    assert all(r.value == f"cfg_{r.name.lower()}" for r in ClientStateErrorReason)
    assert all(r.value == f"api_{r.name.lower()}" for r in ApiCallErrorReason)
    assert all(r.value == f"evo_{r.name.lower()}" for r in EvohomeErrorReason)


# the default reason of each error (used if it is raised with only a message)
_DEFAULT_REASONS: dict[type[exc.EvohomeError], StrEnum] = {
    exc.EvohomeError: EvohomeErrorReason.ERROR_UNSPECIFIED,
    exc.ApiCallFailedError: ApiCallErrorReason.CALL_FAILED,
    exc.ApiCallRejectedError: ApiCallErrorReason.REQUEST_REJECTED,
    exc.ApiRateLimitExceededError: ApiCallErrorReason.RATE_LIMITED,
    exc.AuthRateLimitExceededError: ApiCallErrorReason.RATE_LIMITED,
    exc.AuthenticationFailedError: ApiCallErrorReason.AUTHENTICATION_FAILED,
    exc.BadUserCredentialsError: ApiCallErrorReason.CREDENTIALS_INVALID,
    exc.CommTaskFailedError: ApiCallErrorReason.COMM_TASK_FAILED,
    exc.BadApiRequestError: RequestErrorReason.REQUEST_INVALID,
    exc.InvalidSetModeError: RequestErrorReason.MODE_INVALID,
    exc.InvalidSetScheduleError: RequestErrorReason.SCHEDULE_INVALID,
    exc.BadApiResponseError: ResponseErrorReason.RESPONSE_INVALID,
    exc.InvalidGetConfigError: ResponseErrorReason.CONFIG_INVALID,
    exc.GhostZoneError: ResponseErrorReason.ZONE_INVALID,
    exc.InvalidGetStatusError: ResponseErrorReason.STATUS_INVALID,
    exc.InvalidGetScheduleError: ResponseErrorReason.SCHEDULE_INVALID,
    exc.ClientStateError: ClientStateErrorReason.CONFIG_INVALID,
    exc.NotFetchedError: ClientStateErrorReason.CONFIG_NOT_FETCHED,
    exc.StaleConfigError: ClientStateErrorReason.CONFIG_STALE,
}


def test_every_error_has_a_default_reason() -> None:
    """Test every error (that has a reason) is listed above, with its default."""
    assert set(_DEFAULT_REASONS) == set(_CLASSES)


@pytest.mark.parametrize("cls", _CLASSES, ids=lambda c: c.__name__)
def test_error_without_a_reason(
    cls: type[exc.EvohomeError],
) -> None:
    """Test each error can still be raised with only a message (as before reasons).

    Its reason is then its class's default, so is never None.
    """

    err = cls("a message")  # e.g. as HA's tests do

    assert err.message == "a message"
    assert err.reason is _DEFAULT_REASONS[cls]
    assert err.details == {}


def test_error_with_a_reason() -> None:
    """Test a reason, if given, is used rather than the class's default."""

    err = exc.InvalidGetConfigError(
        "a message", reason=ResponseErrorReason.ACCOUNT_INVALID
    )

    assert err.reason is ResponseErrorReason.ACCOUNT_INVALID


def test_error_caught_as_evohome_error() -> None:
    """Test the reason of an error caught only as an EvohomeError (e.g. as HA does).

    The caller need not know which kind of error it is to use its reason (e.g. as a
    translation key).
    """

    with pytest.raises(exc.EvohomeError) as err:  # i.e. caught as an EvohomeError
        raise exc.InvalidSetModeError(
            "a message", reason=RequestErrorReason.MODE_UNKNOWN, mode="Auto"
        )

    assert err.value.reason is RequestErrorReason.MODE_UNKNOWN
    assert err.value.details == {"mode": "Auto"}
