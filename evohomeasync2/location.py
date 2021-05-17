#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
"""Provide handling of a location."""
from .gateway import Gateway


class Location(object):
    """Provide handling of a location."""

    def __init__(self, client, data=None):
        """Initialise the class."""
        self.client = client
        self._gateways = []
        self.gateways = {}
        self.locationId = None

        if data is not None:
            self.__dict__.update(data["locationInfo"])

            for gw_data in data["gateways"]:
                gateway = Gateway(client, self, gw_data)
                self._gateways.append(gateway)
                self.gateways[gateway.gatewayId] = gateway

    async def status(self):
        """Retrieve the location status."""
        url = (
            "https://tccna.honeywell.com/WebAPI/emea/api/v1/"
            "location/%s/status?includeTemperatureControlSystems=True" % self.locationId
        )

        async with self.client._session.get(
            url,
            headers=await self.client._headers(),
        ) as response:
            response.raise_for_status()
            data = await response.json()

        # Now feed into other elements
        for gw_data in data["gateways"]:
            gateway = self.gateways[gw_data["gatewayId"]]

            for sys in gw_data["temperatureControlSystems"]:
                system = gateway.control_systems[sys["systemId"]]

                system.__dict__.update(
                    {
                        "systemModeStatus": sys["systemModeStatus"],
                        "activeFaults": sys["activeFaults"],
                    }
                )

                if "dhw" in sys:
                    system.hotwater.__dict__.update(sys["dhw"])

                for zone_data in sys["zones"]:
                    zone = system.zones[zone_data["name"]]
                    zone.__dict__.update(zone_data)

        return data
