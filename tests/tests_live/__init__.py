"""Tests against the vendor's real servers (opt-in: see conftest.py).

Each replays the requests recorded in tests/tests_api (v1/vendor.py, v2/vendor.py and
the tests' own payloads), and checks that the vendor still answers as recorded: in its
status, its content type, and its shape (as validated by the schema modules), but not
its values.
"""
