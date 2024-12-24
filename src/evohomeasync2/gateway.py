"""Provides handling of TCC gateways."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, NoReturn

from evohome.helpers import camel_to_snake

from .const import (
    SZ_GATEWAY_ID,
    SZ_GATEWAY_INFO,
    SZ_MAC,
    SZ_SYSTEM_ID,
    SZ_TEMPERATURE_CONTROL_SYSTEMS,
)
from .schemas import factory_gwy_status
from .schemas.const import EntityType
from .system import ControlSystem
from .zone import ActiveFaultsBase

if TYPE_CHECKING:
    import voluptuous as vol

    from . import Location
    from .schemas.typedefs import (
        EvoGwyConfigEntryT,
        EvoGwyConfigResponseT,
        EvoGwyStatusResponseT,
    )


class Gateway(ActiveFaultsBase):
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

        self._config: Final[EvoGwyConfigEntryT] = config[SZ_GATEWAY_INFO]  # type: ignore[misc]
        self._status: EvoGwyStatusResponseT | None = None

        # children
        self.systems: list[ControlSystem] = []
        self.system_by_id: dict[str, ControlSystem] = {}  # tcs by id

        for tcs_entry in config[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            tcs = ControlSystem(self, tcs_entry)

            self.systems.append(tcs)
            self.system_by_id[tcs.id] = tcs

    @property  # TODO: deprecate in favour of .id attr
    def gatewayId(self) -> str:  # noqa: N802
        return self._id

    @property
    def mac_address(self) -> str:
        return self._config[SZ_MAC]

    async def _get_status(self) -> NoReturn:
        """Get the latest state of the gateway and update its status attr.

        It is more efficient to call Location.update() as all descendants are updated
        with a single GET. Returns the raw JSON of the latest state.
        """

        raise NotImplementedError

    def _update_status(self, status: EvoGwyStatusResponseT) -> None:
        """Update the GWY's status and cascade to its descendants."""

        self._update_faults(status["active_faults"])
        self._status = status

        for tcs_status in self._status[SZ_TEMPERATURE_CONTROL_SYSTEMS]:
            if tcs := self.system_by_id.get(tcs_status[SZ_SYSTEM_ID]):
                tcs._update_status(tcs_status)

            else:
                self._logger.warning(
                    f"{self}: system_id='{tcs_status[SZ_SYSTEM_ID]}' not known"
                    ", (has the gateway configuration been changed?)"
                )
