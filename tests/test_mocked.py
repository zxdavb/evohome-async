#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""evohome-async - validate the config & status schemas."""

# import json
from pathlib import Path
import pytest

import evohomeasync2 as evohome


from mocked_server import aiohttp
from schema import SCH_CONFIG, SCH_STATUS


TEST_DIR = Path(__file__).resolve().parent
WORK_DIR = f"{TEST_DIR}/mocked"


@pytest.mark.asyncio
async def test_vendor_api():
    loc_idx: int = 0

    mocked_server = aiohttp.MockedServer(None, None)

    session = aiohttp.ClientSession(mocked_server=mocked_server)

    client = evohome.EvohomeClient("username", "password", session=session)

    assert client.account_info is None
    assert client.installation_info is None
    assert client.locations == []

    await client.login()

    assert SCH_CONFIG(client.installation_info)

    loc_config = client.installation_info[loc_idx]
    assert loc_config

    loc_status = await client.locations[loc_idx].status()
    assert SCH_STATUS(loc_status)

    assert SCH_CONFIG.validate(client.installation_info)
