"""Tests for evohome-async - check the TypedDicts agree with the probatio schemas.

The vendor's API is undocumented, so the Tcc*T TypedDicts are its documentation, and
the Evo*T TypedDicts describe what this library returns - but it is the schemas (built
by the factory_* functions) that actually run. A divergence between the two is a bug.

So, check they agree:
- structurally: the same keys, equally required, nested the same way
- empirically: the vendor's JSON (the fixtures) is valid per the Tcc*T TypedDicts
"""

from __future__ import annotations

import json
import types
from datetime import datetime as dt
from typing import (
    TYPE_CHECKING,
    Any,
    NotRequired,
    Required,
    Union,
    get_args,
    get_origin,
    get_type_hints,
    is_typeddict,
)

import probatio as vol
import pytest

from _evohome.helpers import camel_to_snake
from evohomeasync import schemas as sch0, typedefs as evo0
from evohomeasync2 import const as const2, typedefs as evo2
from evohomeasync2.schemas import account, config, const as sch2_const, schedule, status
from evohomeasync2.schemas.helpers import Case

from .conftest import FIXTURES_V2

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


# the keys of a mapping, each with its required-ness and the shape of its value
type _Shape = dict[str, tuple[bool, _Shape | None]]

# the modules of the TypedDicts import some names only when TYPE_CHECKING
_NS_V0: dict[str, Any] = vars(sch0) | vars(evo0)
_NS_V2_TCC: dict[str, Any] = (
    vars(sch2_const) | vars(account) | vars(config) | vars(schedule) | vars(status)
)
_NS_V2_EVO: dict[str, Any] = vars(const2) | vars(evo2) | {"dt": dt}


def _merge(shapes: list[_Shape | None]) -> _Shape | None:
    """Merge the shapes of alternatives: a key is required only if required by all."""

    maps = [s for s in shapes if s is not None]
    if not maps:
        return None

    result: _Shape = {}
    for key in {k for m in maps for k in m}:
        entries = [m[key] for m in maps if key in m]
        is_required = len(entries) == len(maps) and all(r for r, _ in entries)
        result[key] = (is_required, _merge([s for _, s in entries]))
    return result


def _schema_shape(node: object, *, required: bool = False) -> _Shape | None:
    """Return the shape of a schema (None if it doesn't validate a mapping's keys)."""

    if isinstance(node, vol.Schema):
        return _schema_shape(node.schema, required=node.required)

    if isinstance(node, dict):
        result: _Shape = {}
        for key, value in node.items():
            if isinstance(key, vol.Required):
                name, is_required = key.schema, True
            elif isinstance(key, vol.Optional):
                name, is_required = key.schema, False
            else:
                name, is_required = key, required
            if isinstance(name, str):  # not e.g. {str: dict}
                result[name] = (is_required, _schema_shape(value))
        return result or None

    if isinstance(node, list):  # e.g. [SCH_ZONE]
        return _merge([_schema_shape(n) for n in node])

    if isinstance(node, vol.Any | vol.All | vol.Union):
        return _merge([_schema_shape(n) for n in node.validators])

    return None


def _typeddict_shape(tp: object, ns: dict[str, Any]) -> _Shape | None:
    """Return the shape of a TypedDict (None if the type is not a TypedDict)."""

    if is_typeddict(tp):
        result: _Shape = {}
        hints = get_type_hints(tp, globalns=ns, localns=ns, include_extras=True)
        for key, hint in hints.items():
            value, is_required = hint, bool(getattr(tp, "__total__", True))
            if (origin := get_origin(hint)) is NotRequired or origin is Required:
                (value,), is_required = get_args(hint), origin is Required
            result[key] = (is_required, _typeddict_shape(value, ns))
        return result

    if get_origin(tp) is list:
        return _typeddict_shape(get_args(tp)[0], ns)

    if get_origin(tp) in (Union, types.UnionType):
        return _merge([_typeddict_shape(t, ns) for t in get_args(tp)])

    return None


def _differences(
    schema: _Shape | None, typeddict: _Shape | None, path: str = ""
) -> list[str]:
    """Return how the shape of a schema differs from that of a TypedDict."""

    if schema is None:  # the schema doesn't validate the keys, so nothing to compare
        return []

    typeddict = typeddict or {}

    result: list[str] = []
    for key in sorted(schema.keys() | typeddict.keys()):
        where = f"{path}.{key}"

        if key not in typeddict:
            result.append(f"{where}: is only in the schema")
        elif key not in schema:
            result.append(f"{where}: is only in the TypedDict")

        else:
            (sch_required, sch_value), (td_required, td_value) = (
                schema[key],
                typeddict[key],
            )
            if sch_required != td_required:
                result.append(
                    f"{where}: required={sch_required} in the schema, "
                    f"but required={td_required} in the TypedDict"
                )
            result.extend(_differences(sch_value, td_value, where))

    return result


# v0: factory_*(camel_to_snake) and its Evo*DictT - the v0 Tcc*T are not compared, as
# the v0 schemas deliberately don't require keys that this library doesn't use
V0_SCHEMAS: dict[str, tuple[Callable[[Callable[[str], str]], object], object]] = {
    "failure": (sch0.factory_failure_response, evo0.EvoFailureDictT),
    "account_info": (
        sch0.factory_user_account_info_response,
        evo0.EvoUserAccountInfoDictT,
    ),
    "session": (sch0.factory_session_response, evo0.EvoSessionDictT),
    "locations": (sch0.factory_location_response_list, evo0.EvoTcsInfoDictT),
}


@pytest.mark.parametrize("name", V0_SCHEMAS)
def test_v0_pythonic_typeddicts(name: str) -> None:
    """Test the v0 schemas (with snake_case keys) agree with their Evo*DictT."""

    factory, evo_type = V0_SCHEMAS[name]

    diffs = _differences(
        _schema_shape(factory(camel_to_snake)), _typeddict_shape(evo_type, _NS_V0)
    )
    assert not diffs, "\n".join(diffs)


# v2: factory_*(case), its Tcc*T (Case.VENDOR) and its Evo*T (Case.PYTHONIC), if any
V2_SCHEMAS: dict[str, tuple[Callable[[Case], object], object, object]] = {
    "loc_status": (
        status.factory_loc_status,
        status.TccLocStatusResponseT,
        evo2.EvoLocStatusResponseT,
    ),
    "gwy_status": (
        status.factory_gwy_status,
        status.TccGwyStatusResponseT,
        evo2.EvoGwyStatusResponseT,
    ),
    "tcs_status": (
        status.factory_tcs_status,
        status.TccTcsStatusResponseT,
        evo2.EvoTcsStatusResponseT,
    ),
    "zon_status": (
        status.factory_zon_status,
        status.TccZonStatusResponseT,
        evo2.EvoZonStatusResponseT,
    ),
    "dhw_status": (
        status.factory_dhw_status,
        status.TccDhwStatusResponseT,
        evo2.EvoDhwStatusResponseT,
    ),
    "active_faults": (
        status.factory_active_faults,
        status.TccActiveFaultResponseT,
        evo2.EvoActiveFaultT,
    ),
    "dhw_schedule": (
        schedule.factory_dhw_schedule,
        schedule.TccDhwDailySchedulesT,
        evo2.EvoDhwScheduleResponseT,
    ),
    "zon_schedule": (
        schedule.factory_zon_schedule,
        schedule.TccZonDailySchedulesT,
        evo2.EvoZonScheduleResponseT,
    ),
    "user_account": (
        account.factory_user_account,
        account.TccUsrAccountResponseT,
        evo2.EvoUsrAccountResponseT,
    ),
    "oauth_token": (
        account.factory_post_oauth_token,
        account.TccOAuthTokenResponseT,
        evo2.EvoAuthTokensResponseT,
    ),
    "error_response": (
        account.factory_error_response,
        account.TccErrorResponseT,
        None,
    ),
    "status_response": (
        account.factory_status_response,
        account.TccFailureResponseT,  # a list of these
        None,
    ),
    "loc_config": (
        config.factory_location_installation_info,
        config.TccLocConfigResponseT,
        evo2.EvoLocConfigResponseT,
    ),
    "gwy_config": (
        config.factory_gateway,
        config.TccGwyConfigResponseT,
        evo2.EvoGwyConfigResponseT,
    ),
    "tcs_config": (
        config.factory_tcs,
        config.TccTcsConfigResponseT,
        evo2.EvoTcsConfigResponseT,
    ),
    "zon_config": (
        config.factory_zone,
        config.TccZonConfigResponseT,
        evo2.EvoZonConfigResponseT,
    ),
    "dhw_config": (
        config.factory_dhw,
        config.TccDhwConfigResponseT,
        evo2.EvoDhwConfigResponseT,
    ),
    "time_zone": (
        config.factory_time_zone,
        config.TccTimeZoneInfoT,
        evo2.EvoTimeZoneT,
    ),
}


@pytest.mark.parametrize("name", [k for k, v in V2_SCHEMAS.items() if v[2] is not None])
def test_v2_pythonic_typeddicts(name: str) -> None:
    """Test the v2 pythonic schemas (snake_case keys) agree with their Evo*T."""

    factory, _, evo_type = V2_SCHEMAS[name]

    diffs = _differences(
        _schema_shape(factory(Case.PYTHONIC)), _typeddict_shape(evo_type, _NS_V2_EVO)
    )
    assert not diffs, "\n".join(diffs)


@pytest.mark.parametrize("name", V2_SCHEMAS)
def test_v2_vendor_typeddicts(name: str) -> None:
    """Test the v2 vendor schemas (camelCase keys) agree with their Tcc*T."""

    factory, tcc_type, _ = V2_SCHEMAS[name]

    diffs = _differences(
        _schema_shape(factory(Case.VENDOR)), _typeddict_shape(tcc_type, _NS_V2_TCC)
    )
    assert not diffs, "\n".join(diffs)


# the vendor's JSON (fixtures), and the schema built from the TypedDict it should match
FIXTURE_TYPEDDICTS: dict[str, vol.Schema] = {
    "user_account.json": vol.TypedDictSchema(account.TccUsrAccountResponseT),
    "user_locations.json": vol.Schema(
        [vol.TypedDictSchema(config.TccLocConfigResponseT)]
    ),
    "status_*.json": vol.TypedDictSchema(status.TccLocStatusResponseT),
    "schedule_dhw.json": vol.TypedDictSchema(schedule.TccDhwDailySchedulesT),
    "schedule_zone.json": vol.TypedDictSchema(schedule.TccZonDailySchedulesT),
    "schedule_[0-9]*.json": vol.TypedDictSchema(schedule.TccZonDailySchedulesT),
}


@pytest.mark.parametrize(
    ("pattern", "path"),
    [
        pytest.param(pattern, path, id=f"{path.parent.name}/{path.name}")
        for pattern in FIXTURE_TYPEDDICTS
        for path in sorted(FIXTURES_V2.glob(f"*/{pattern}"))
    ],
)
def test_v2_fixtures_typeddicts(pattern: str, path: Path) -> None:
    """Test the vendor's JSON (as per the fixtures) is valid per the Tcc*T."""

    FIXTURE_TYPEDDICTS[pattern](json.loads(path.read_text()))
