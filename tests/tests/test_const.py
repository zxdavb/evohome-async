"""Tests for evohome-async v2 schema - validate completeness of constants and enums."""

from __future__ import annotations

import inspect
from enum import StrEnum

import evohomeasync2.const as evo_const
import evohomeasync2.schemas.const as tcc_const
from _evohome.helpers import camel_to_snake

# Pythonic SZ_* constants with no vendor equivalent (keys invented by the library)
NON_TCC_SZ = {"SZ_ID", "SZ_SCHEDULE", "SZ_SETPOINT", "SZ_THERMOSTAT"}


# Tcc* enums that intentionally have no user-facing counterpart
EXCLUDED_TCC_ENUMS = {
    "TccEntityType",  # values are URL path segments, not user-visible
}


def test_evo_str_constants_complete_and_correct() -> None:
    """Check all vendor constants are reproduced as snake_case, not camelCase.

    Every S2_* str in schemas/const.py should have a user-facing SZ_* in const.py,
    and vice versa (bar known non-vendor exceptions).
    """

    s2 = {
        n: v
        for n, v in vars(tcc_const).items()
        if n.startswith("S2_") and isinstance(v, str)
    }
    sz = {
        n: v
        for n, v in vars(evo_const).items()
        if n.startswith("SZ_") and isinstance(v, str)
    }

    # 1. every vendor's S2_ has a corresponding pythonic SZ_
    missing = {f"SZ_{n[3:]}" for n in s2 if f"SZ_{n[3:]}" not in sz}
    assert not missing, f"S2_ constants with no SZ_ equivalent: {sorted(missing)}"

    # 2. every pythonic SZ_ (except non-vendor ones) has a corresponding vendor's S2_
    extra = {n for n in sz if f"S2_{n[3:]}" not in s2} - NON_TCC_SZ
    assert not extra, f"SZ_ constants with no S2_ source: {sorted(extra)}"

    # 3. every matched pair (by name)has the correct value
    wrong = {
        n: (v, camel_to_snake(s2[f"S2_{n[3:]}"]))
        for n, v in sz.items()
        if f"S2_{n[3:]}" in s2 and v != camel_to_snake(s2[f"S2_{n[3:]}"])
    }
    assert not wrong, f"SZ_ values don't match camel_to_snake(S2_): {wrong}"


def test_evo_str_enums_complete_and_correct() -> None:
    """Check all vendor StrEnums are reproduced as snake_case, not PascalCase.

    Every Tcc* StrEnum in schemas/const.py should have a user-facing StrEnum in const.py
    (name = Tcc stripped) and vice versa (bar known exceptions).
    """

    tcc_enums = {
        n: cls
        for n, cls in vars(tcc_const).items()
        if n.startswith("Tcc")
        and inspect.isclass(cls)
        and issubclass(cls, StrEnum)
        and n not in EXCLUDED_TCC_ENUMS
    }
    evo_enums = {
        n: cls
        for n, cls in vars(evo_const).items()
        if inspect.isclass(cls)
        and issubclass(cls, StrEnum)
        and not n.startswith("Tcc")
        and cls.__module__ == evo_const.__name__  # defined here, not re-exported
    }

    # 1. every Tcc* has a user-facing counterpart (name = Tcc stripped)
    missing = {n[3:] for n in tcc_enums if n[3:] not in evo_enums}
    assert not missing, f"Tcc* enums with no user-facing counterpart: {sorted(missing)}"

    # 2. every user-facing StrEnum has a Tcc* source
    extra = {n for n in evo_enums if f"Tcc{n}" not in tcc_enums}
    assert not extra, f"User-facing enums with no Tcc* source: {sorted(extra)}"

    # 3. every member in a user-facing enum equals camel_to_snake of the Tcc* member
    for tcc_name, tcc_cls in tcc_enums.items():
        evo_cls = evo_enums[tcc_name[3:]]
        tcc_members = {m.name: m.value for m in tcc_cls}
        evo_members = {m.name: m.value for m in evo_cls}

        assert tcc_members.keys() == evo_members.keys(), (
            f"{tcc_name} and {evo_cls.__name__} have different members: "
            f"extra in Tcc={sorted(tcc_members.keys() - evo_members.keys())}, "
            f"extra in Evo={sorted(evo_members.keys() - tcc_members.keys())}"
        )
        wrong = {
            name: (evo_members[name], camel_to_snake(tcc_members[name]))
            for name in tcc_members
            if evo_members[name] != camel_to_snake(tcc_members[name])
        }
        assert not wrong, (
            f"{evo_cls.__name__} values don't match camel_to_snake({tcc_name}): {wrong}"
        )
