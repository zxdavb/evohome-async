"""Tests for evohome-async - validate the exception hierarchy."""

from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest

import evohomeasync
import evohomeasync2
from _evohome import exceptions as exc

if TYPE_CHECKING:
    from types import ModuleType

# Every exception, and its immediate parent(s)
HIERARCHY: dict[type[exc.EvohomeError], tuple[type[exc.EvohomeError], ...]] = {
    exc.ApiCallFailedError: (exc.EvohomeError,),
    exc.ApiRateLimitExceededError: (exc.ApiCallFailedError,),
    exc.AuthenticationFailedError: (exc.ApiCallFailedError,),
    exc.AuthRateLimitExceededError: (
        exc.ApiRateLimitExceededError,
        exc.AuthenticationFailedError,
    ),
    exc.BadUserCredentialsError: (exc.AuthenticationFailedError,),
    exc.RequestRejectedError: (exc.ApiCallFailedError,),
    #
    exc.BadApiResponseError: (exc.EvohomeError,),
    exc.InvalidConfigError: (exc.BadApiResponseError,),
    exc.GhostZoneError: (exc.InvalidConfigError,),
    exc.InvalidStatusError: (exc.BadApiResponseError,),
    exc.InvalidScheduleError: (exc.BadApiResponseError,),
    #
    exc.BadApiRequestError: (exc.EvohomeError,),
    exc.InvalidModeError: (exc.BadApiRequestError,),
    exc.InvalidScheduleUploadedError: (exc.BadApiRequestError,),
    #
    exc.ClientStateError: (exc.EvohomeError,),
    exc.NotFetchedError: (exc.ClientStateError,),
    exc.StaleConfigError: (exc.ClientStateError,),
    exc.NoSingleTcsError: (exc.ClientStateError,),
}

# The deprecated names, and the names that replaced them
DEPRECATED_ALIASES: dict[str, str] = {
    "ApiRequestFailedError": "ApiCallFailedError",
    "BadScheduleUploadedError": "InvalidScheduleUploadedError",
}

# As above, but only for v2 (v1 has never exported the mode exceptions)
DEPRECATED_ALIASES_V2: dict[str, str] = {
    "InvalidSystemModeError": "InvalidModeError",
}


@pytest.mark.parametrize(
    ("cls", "bases"), HIERARCHY.items(), ids=[c.__name__ for c in HIERARCHY]
)
def test_hierarchy(
    cls: type[exc.EvohomeError], bases: tuple[type[exc.EvohomeError], ...]
) -> None:
    """Test each exception has the expected parent(s)."""

    assert cls.__bases__ == bases


def test_hierarchy_is_complete() -> None:
    """Test every public exception of the module is in the hierarchy, above."""

    classes = {
        v
        for k, v in vars(exc).items()
        if isinstance(v, type)
        and issubclass(v, exc.EvohomeError)
        and not k.startswith("_")
    }

    assert classes == {exc.EvohomeError, *HIERARCHY}


@pytest.mark.parametrize("module", [exc, evohomeasync, evohomeasync2])
@pytest.mark.parametrize(("old_name", "new_name"), DEPRECATED_ALIASES.items())
def test_deprecated_aliases(module: ModuleType, old_name: str, new_name: str) -> None:
    """Test each deprecated name is still available, as an alias of the new name."""

    assert getattr(module, old_name) is getattr(module, new_name)


@pytest.mark.parametrize("module", [exc, evohomeasync2])
@pytest.mark.parametrize(("old_name", "new_name"), DEPRECATED_ALIASES_V2.items())
def test_deprecated_aliases_v2(
    module: ModuleType, old_name: str, new_name: str
) -> None:
    """Test each deprecated v2 name is still available, as an alias of the new name."""

    assert getattr(module, old_name) is getattr(module, new_name)


@pytest.mark.parametrize("package", [evohomeasync, evohomeasync2])
def test_packages_export_the_hierarchy(package: ModuleType) -> None:
    """Test each package exports the exceptions, as they are in the hierarchy."""

    names: list[str] = package.exceptions.__all__

    assert set(names) <= set(package.__all__)

    for name in names:
        assert getattr(package, name) is getattr(exc, name)
        assert getattr(package.exceptions, name) is getattr(exc, name)


def test_call_failures_have_a_status() -> None:
    """Test the attrs of the exceptions for the failure of an API call."""

    err = exc.ApiCallFailedError("message")

    assert err.message == "message"
    assert err.status is None

    err = exc.BadUserCredentialsError("message", status=HTTPStatus.BAD_REQUEST)

    assert err.status == HTTPStatus.BAD_REQUEST


@pytest.mark.parametrize(
    "cls", [exc.ApiRateLimitExceededError, exc.AuthRateLimitExceededError]
)
def test_rate_limit_failures_have_a_retry_after(
    cls: type[exc.ApiRateLimitExceededError],
) -> None:
    """Test the attrs of the exceptions for exceeding a rate limit."""

    retry_after = 30.0

    err = cls("message")

    assert err.message == "message"
    assert err.status == HTTPStatus.TOO_MANY_REQUESTS
    assert err.retry_after is None

    err = cls("message", retry_after=retry_after)

    assert err.status == HTTPStatus.TOO_MANY_REQUESTS
    assert err.retry_after == retry_after
