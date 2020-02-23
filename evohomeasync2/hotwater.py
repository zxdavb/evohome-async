"""Provides handling of the hot water zone."""
from .zone import ZoneBase


class HotWater(ZoneBase):
    """Provides handling of the hot water zone."""

    def __init__(self, client, data):
        super(HotWater, self).__init__(client)

        self.dhwId = None  # pylint: disable=invalid-name

        self.__dict__.update(data)

        self.name = ""
        self.zoneId = self.dhwId
        self.zone_type = "domesticHotWater"

    async def _set_dhw(self, data):
        headers = dict(await self.client._headers())  # pylint: disable=protected-access
        headers["Content-Type"] = "application/json"

        url = (
            "https://tccna.honeywell.com/WebAPI/emea/api/v1"
            "/domesticHotWater/%s/state" % self.dhwId
        )

        async with self.client._session.put(
            url, json=data, headers=headers
        ) as response:
            response.raise_for_status()

    async def set_dhw_on(self, until=None):
        """Sets the DHW on until a given time, or permanently."""
        if until is None:
            data = {"Mode": "PermanentOverride", "State": "On", "UntilTime": None}
        else:
            data = {
                "Mode": "TemporaryOverride",
                "State": "On",
                "UntilTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        await self._set_dhw(data)

    async def set_dhw_off(self, until=None):
        """Sets the DHW off until a given time, or permanently."""
        if until is None:
            data = {"Mode": "PermanentOverride", "State": "Off", "UntilTime": None}
        else:
            data = {
                "Mode": "TemporaryOverride",
                "State": "Off",
                "UntilTime": until.strftime("%Y-%m-%dT%H:%M:%SZ"),
            }

        await self._set_dhw(data)

    async def set_dhw_auto(self):
        """Sets the DHW to follow the schedule."""
        data = {"Mode": "FollowSchedule", "State": "", "UntilTime": None}

        await self._set_dhw(data)
