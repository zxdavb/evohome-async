"""Provides handling of TCC gateways."""

from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Final, NoReturn

from _evohome.helpers import camel_to_snake

from .const import (
    SZ_GATEWAY_ID,
    SZ_GATEWAY_INFO,
    SZ_MAC,
    SZ_SYSTEM_ID,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
)
from .control_system import ControlSystem
from .schemas import factory_gwy_status
from .schemas.const import EntityType
from .zone import ActiveFaultsBase, EntityBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import Location
    from .schemas.typedefs import (
        EvoGwyConfigEntryT,
        EvoGwyConfigResponseT,
        EvoGwyStatusResponseT,
    )


class Gateway(ActiveFaultsBase, EntityBase):
    """Instance of a location's gateway."""

    SCH_STATUS: vol.Schema = factory_gwy_status(camel_to_snake)
    _TYPE = EntityType.GWY

    def __init__(self, location: Location, config: EvoGwyConfigResponseT) -> None:
        super().__init__(
            config[SZ_GATEWAY_INFO][SZ_GATEWAY_ID],
            location._auth,
            location._logger,
        )

        self.location = location  # parent
        #

        # children
        self.systems: list[ControlSystem] = []
        self.system_by_id: dict[str, ControlSystem] = {}  # tcs by id

        self._config: Final[EvoGwyConfigEntryT] = config[SZ_GATEWAY_INFO]  # type: ignore[misc]

        for tcs_entry in config[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = ControlSystem(self, tcs_entry)

            self.systems.append(tcs)
            self.system_by_id[tcs.id] = tcs

        self._status: EvoGwyStatusResponseT | None = None

    @property
    def config(self) -> EvoGwyConfigEntryT:
        """Return the latest config of the entity."""
        return self._config

    @property
    def status(self) -> EvoGwyStatusResponseT:
        """Return the latest status of the entity."""
        return super().status  # type: ignore[return-value]

    # Config attrs...

    @cached_property  # RENAMED val: was mac
    def mac_address(self) -> str:
        return self._config[SZ_MAC]

    # Status (state) attrs & methods...

    async def _get_status(self) -> NoReturn:
        """Get the latest state of the gateway and update its status attr.

        It is more efficient to call Location.update() as all descendants are updated
        with a single GET. Returns the raw JSON of the latest state.
        """

        raise NotImplementedError

    def _update_status(self, status: EvoGwyStatusResponseT) -> None:
        """Update the GWY's status and cascade to its descendants."""

        self._update_faults(status["active_faults"])

        # break the TypedDict into its parts (so, ignore[misc])...
        for tcs_status in status.pop(SZ_TEMPERATURE_CONTROL_SYSTEMS):  # type: ignore[misc]
            if tcs := self.system_by_id.get(tcs_status[SZ_SYSTEM_ID]):
                tcs._update_status(tcs_status)

            else:
                self._logger.warning(
                    f"{self}: system_id='{tcs_status[SZ_SYSTEM_ID]}' not known"
                    ", (has the gateway configuration been changed?)"
                )

        self._status = status
