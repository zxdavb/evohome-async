#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Mocked vendor server for provision via a hacked aiohttp."""
from __future__ import annotations


_DEBUG_USE_MOCK_AIOHTTP = True
_DISABLE_STRICT_ASSERTS = False  # of response content-type, schema
