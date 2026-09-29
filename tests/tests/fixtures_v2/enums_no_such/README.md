# fixtures_v2/enums_no_such

Synthesised: coverage of enum values that are **not** members of their `Tcc*` enums.

## System

Minimal, based on `default/`: location 4001021, gateway 4001022, TCS 4001023, one zone
(4001024), no DHW.

## Notes

The vendor's enums are incompletely documented, so an unexpected value must not reject
the entire response (see: evohome-async
[#145](https://github.com/zxdavb/evohome-async/issues/145), HA core
[#178493](https://github.com/home-assistant/core/issues/178493),
[#179414](https://github.com/home-assistant/core/issues/179414)). This fixture has one
such value for each of the enums that tolerate them (via `factory_enum_or_str()`):

| Enum | Entity | Field | Value |
|------|--------|-------|-------|
| `TccTcsModelType` | TCS 4001023 | `modelType` | `NoSuchModelType` |
| `TccZoneModelType` | zone 4001024 | `modelType` | `NoSuchModelType` |
| `TccZoneType` | zone 4001024 | `zoneType` | `NoSuchZoneType` |
| `TccFaultType` | gateway 4001022 | `faultType` | `NoSuchFaultType` |
| `TccFanMode` | zone 4001024 | `allowedFanModes[].fanMode` (config) | `NoSuchFanMode` |
| `TccFanMode` | zone 4001024 | `fanStatus.fanMode` (status) | `NoSuchFanMode` |

Each is passed through as a (snake_case) str, and logged as unknown. A fan mode is logged
only from the config (`allowedFanModes`), as the status reports one of those.

These values are deliberately not enum members (and never will be). Do not "fix" them by
adding them to the enums, as that would silently remove this coverage.

For the vendor's own `Unknown` values, see `enums_unknown/`.
