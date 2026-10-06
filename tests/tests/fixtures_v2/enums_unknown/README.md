# fixtures_v2/enums_unknown

Synthesised: coverage of the vendor's own `Unknown` enum values.

## System

Minimal, based on `default/`: location 4001031, gateway 4001032, TCS 4001033, two zones
(4001034, 4001035), no DHW.

## Notes

Only `TccZoneModelType` and `TccZoneType` have an `Unknown` member (see: HA core
[#30945](https://github.com/home-assistant/core/issues/30945)); `TccTcsModelType` and
`TccFaultType` do not.

Such a zone is a ghost zone, and is ignored as invalid. There are two zones, as the
`modelType` is checked before the `zoneType`, so one zone cannot cover both:

| Zone | `modelType` | `zoneType` | Rejected by |
|------|-------------|------------|-------------|
| 4001034 | `Unknown` | `RadiatorZone` | `modelType` |
| 4001035 | `HeatingZone` | `Unknown` | `zoneType` |

The real fixtures with ghost zones (`evohome_017/`, `hass_101355/`, `hass_110065/`) have
both fields as `Unknown`, so never reach the `zoneType` check.

For values that are not enum members at all, see `enums_no_such/`.
