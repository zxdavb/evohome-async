# fixtures_v2/hass_067822

Source: [Home Assistant core issue #67822](https://github.com/home-assistant/core/issues/67822)

## System

- Location: 3184115 (United Kingdom)
- Gateway: 2937956
- TCS: 4187037
- 12 zones: Living Room (4187036), Dining Room (4217766), Entrance (4217767),
  Laundry room (4217768), Sebastians Room (4217769), Sophies Room (4217770),
  Guest Bedroom (4217771), Master Closet (4217772), Master Bedroom (4217773),
  Garage (4217774), Office & Library (4217775), Master Bath (4217776)
- DHW: 6329746
- Timezone: `GMTStandardTime` (UTC+00:00, assumed — not in original)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000011, UK |
| `user_locations.json` | Synthesised TCS from status zones (status-only report) |
| `status_3184115.json` | From `schemas_0/hass_067822/status.json` |

## Notes

- **Status-only fixture** — the original report contained no config, only status.
  The `user_locations.json` TCS was synthesised from the status zone list using standard
  EvoTouch capabilities (`maxHeatSetpoint: 35`, `minHeatSetpoint: 5`, etc.).
- Timezone could not be determined from the status-only data; `GMTStandardTime` used as default.
- Migrated from `schemas_0` format.
