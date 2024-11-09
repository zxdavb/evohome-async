#!/usr/bin/env python3
"""Tests for evohome-async - validate the helper functions."""

from __future__ import annotations

from pathlib import Path

from evohomeasync2.schema.helpers import camel_case, pascal_case

from .common import TEST_DIR

WORK_DIR = Path(f"{TEST_DIR}/schedules")


def test_helper_function() -> None:
    """Test helper functions."""

    CAMEL_CASE = "testString"
    PASCAL_CASE = "TestString"

    assert camel_case(CAMEL_CASE) == CAMEL_CASE
    assert camel_case(PASCAL_CASE) == CAMEL_CASE
    assert pascal_case(CAMEL_CASE) == PASCAL_CASE
    assert pascal_case(PASCAL_CASE) == PASCAL_CASE

    assert camel_case(pascal_case(CAMEL_CASE)) == CAMEL_CASE
    assert pascal_case(camel_case(PASCAL_CASE)) == PASCAL_CASE
