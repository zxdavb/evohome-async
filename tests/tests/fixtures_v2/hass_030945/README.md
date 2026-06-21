# fixtures_v2/hass_030945

Source: [Home Assistant core issue #30945](https://github.com/home-assistant/core/issues/30945)

## System

- Location: 1234567 (United Kingdom)
- Gateway: 2345678
- TCS: 3432522
- 8 zones: Main Room (3432521), Front Room (3432576), Kitchen (3432577),
  Bedroom (3432578), Beans Room (3432579), Noos Room (3432580),
  Bathroom (3449703), Zone Valve (3449740)
- DHW: 3933910
- Timezone: `GMTStandardTime` (UTC+00:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000009, UK |
| `user_locations.json` | Migrated from `schemas_0/hass_030945/config.json`; PII replaced |
| `status_1234567.json` | From `schemas_0/hass_030945/status.json` |

## Notes

- Migrated from `schemas_0` format (no `locationId` in `locationInfo`, no `gatewayInfo`).
- Location ID 1234567 is likely a placeholder in the original report; kept as-is.
