"""Tests for evohome-async - the deprecated names warn, but still work.

The deprecated methods (the `update()`s) are tested in test_client_setup.py.
"""

from __future__ import annotations

import importlib

import pytest

import _evohome.exceptions as exc
import evohomeasync2 as ec2

# (module, deprecated name, its replacement)
ALIASES = [
    (module, "ApiRequestFailedError", exc.ApiCallFailedError)
    for module in (
        "_evohome.exceptions",
        "evohomeasync",
        "evohomeasync.exceptions",
        "evohomeasync2",
        "evohomeasync2.exceptions",
    )
] + [
    (module, "InvalidSystemModeError", exc.InvalidModeRequestError)
    for module in ("_evohome.exceptions", "evohomeasync2", "evohomeasync2.exceptions")
]


@pytest.mark.parametrize(("module", "name", "new"), ALIASES)
def test_alias_warns(
    module: str,
    name: str,
    new: type[exc.EvohomeError],
) -> None:
    """Test a deprecated alias warns (naming its replacement), and is its replacement."""

    mod = importlib.import_module(module)

    with pytest.warns(DeprecationWarning, match=f"use {new.__name__} instead"):
        alias = getattr(mod, name)

    assert alias is new


def _catch_with_alias(err: exc.ApiCallFailedError) -> exc.ApiCallFailedError:
    """Raise the error, and catch it with a deprecated alias (as HA's except clauses)."""

    try:
        raise err
    except ec2.ApiRequestFailedError as caught:
        return caught


def test_alias_still_catches() -> None:
    """Test an except clause with a deprecated alias still catches its replacement."""

    err = exc.ApiCallFailedError("no reply")

    with pytest.warns(DeprecationWarning, match="use ApiCallFailedError instead"):
        caught = _catch_with_alias(err)

    assert caught is err


@pytest.mark.parametrize(
    ("module", "name"),
    [
        ("evohomeasync", "InvalidSystemModeError"),  # v1 has never exported it
        ("evohomeasync2", "NoSuchError"),
        ("_evohome.exceptions", "NoSuchError"),
    ],
)
def test_unknown_name_raises(
    module: str,
    name: str,
) -> None:
    """Test a name that isn't a (deprecated) alias still raises AttributeError."""

    mod = importlib.import_module(module)

    with pytest.raises(AttributeError, match=f"has no attribute {name!r}"):
        getattr(mod, name)
