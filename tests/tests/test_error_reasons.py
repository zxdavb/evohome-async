"""Test the reasons of the errors.

The reasons are public API (e.g. HA may map each one to its own translated message).
Each error class has a default reason (e.g. RATE_LIMITED, for an
ApiRateLimitExceededError), so an error is raised with a reason only if it is not its
class's default (and every reason is never None).
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

# the deprecated aliases that are served by __getattr__ (so are not in vars(exc))
_BY_NAME |= {
    "ApiRequestFailedError": exc.ApiCallFailedError,
    "InvalidSystemModeError": exc.InvalidSetModeError,
}

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


def test_errors_omit_their_default() -> None:
    """Test no error is created with its class's default reason (it is implicit).

    Every call is checked (not only raises), as some are created to be raised later.
    """

    enums = {e.__name__: e for e in _ENUMS}

    calls: list[str] = []
    defaults: list[str] = []

    for path, module in _modules():
        for node in ast.walk(module):
            if (
                not isinstance(node, ast.Call)
                or (cls := _BY_NAME.get(_name(node))) is None
            ):
                continue
            calls.append(site := f"{path}:{node.lineno}")

            reason = _reason(node)
            if (  # e.g. reason=ApiCallErrorReason.RATE_LIMITED
                isinstance(reason, ast.Attribute)
                and isinstance(reason.value, ast.Name)
                and (enum := enums.get(reason.value.id)) is not None
                and enum[reason.attr] is cls._default_reason
            ):
                defaults.append(site)

    assert calls, "no calls were found (has the source moved?)"
    assert not defaults, f"created with its default reason: {defaults}"


# the keyword arguments of an error that are not its details
_NOT_DETAILS = {"message", "reason", "response", "retry_after", "status"}


def test_reasons_have_fixed_details() -> None:
    """Test each reason has the same details (keys) wherever its error is created.

    So that a caller can rely upon them (e.g. as the placeholders of a translated
    message). A reason that is computed (e.g. from an HTTP status) is not checked, and
    only an ApiCallFailedError may unpack its details (the vendor's code, if any).
    """

    enums = {e.__name__: e for e in _ENUMS}

    keys: dict[StrEnum, dict[frozenset[str], list[str]]] = {}
    unpacked: list[str] = []

    for path, module in _modules():
        for node in ast.walk(module):
            if not isinstance(node, ast.Call):
                continue
            if (cls := _BY_NAME.get(_name(node))) is None:
                continue
            site = f"{path}:{node.lineno}"

            reason = _reason(node)
            if reason is None:  # the class's default
                member: StrEnum = cls._default_reason
            elif (
                isinstance(reason, ast.Attribute)
                and isinstance(reason.value, ast.Name)
                and (enum := enums.get(reason.value.id)) is not None
            ):
                member = enum[reason.attr]
            else:  # it is computed (e.g. from an HTTP status)
                continue

            if any(k.arg is None for k in node.keywords) and not issubclass(
                cls, exc.ApiCallFailedError
            ):
                unpacked.append(site)

            names = frozenset(
                k.arg
                for k in node.keywords
                if k.arg is not None and k.arg not in _NOT_DETAILS
            )
            keys.setdefault(member, {}).setdefault(names, []).append(site)

    assert keys, "no calls were found (has the source moved?)"
    assert not unpacked, f"details unpacked (so not fixed): {unpacked}"

    differ = {
        repr(m): {tuple(sorted(n)): sites for n, sites in by_names.items()}
        for m, by_names in keys.items()
        if len(by_names) > 1
    }
    assert not differ, f"reasons with differing details: {differ}"


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
