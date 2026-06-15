"""Tests for evohome-async - helper functions."""

from __future__ import annotations

import inspect
import json
from datetime import datetime as dt
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
import yaml
from freezegun.api import FakeDatetime  # to check schedules, setpoints

if TYPE_CHECKING:
    import voluptuous as vol


def assert_schema(folder: Path, schema: vol.Schema, file_name: str) -> None:
    if not Path(folder).joinpath(file_name).is_file():
        pytest.skip(f"No {file_name} in: {folder.name}")

    with Path(folder).joinpath(file_name).open() as f:
        data: dict[str, Any] = json.load(f)  # is camelCase, as per vendor's schema

    _ = schema(data)


def datetime_representer(dumper: yaml.Dumper, data: dt) -> yaml.nodes.ScalarNode:
    """Represent a datetime as an ISO 8601 string (with a 'T', not a space)."""
    return dumper.represent_scalar("tag:yaml.org,2002:str", data.isoformat())


yaml.add_representer(dt, datetime_representer)
yaml.add_representer(FakeDatetime, datetime_representer)


def get_property_methods(obj: object) -> list[str]:
    """Return a list of property methods of an object."""
    return [
        name
        for name, value in inspect.getmembers(obj.__class__)
        if isinstance(value, property | cached_property)
    ]


def serializable_attrs(obj: object) -> dict[str, str]:
    """Return a dictionary of serializable attributes of an object."""

    result = {}
    for k in get_property_methods(obj) + list(vars(obj).keys()):
        if not k.startswith("_"):
            try:
                result[k] = yaml.dump(getattr(obj, k))
            except TypeError:  # non-serializable, e.g. client, gateways, zone_by_name
                continue

    return result
