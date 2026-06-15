# fixtures_v2/hass_000002

Source: [Home Assistant core issue #000002](https://github.com/home-assistant/core/issues/000002)

## System

- Location: 2738909 (United Kingdom)
- Gateway: 2499896
- TCS: 3432522
- 9 zones: Dead Zone (3432521), Main Room (3432576), Front Room (3432577),
  Kitchen (3432578), Bathroom Dn (3432579), Main Bedroom (3432580),
  Kids Room (3449703), Bathroom Up (3449740), Spare Room (3450733)
- DHW: 3933910
- Timezone: `GMTStandardTime` (UTC+00:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000008, UK |
| `user_locations.json` | Migrated from `schemas_0/hass_000002/config.json`; PII replaced |
| `status_2738909.json` | From `schemas_0/hass_000002/status.json` |
| `temperatures.json` | Temperature log from original report (informational) |

## Notes

- Same location/gateway/system IDs as `default/`, `hass_000000/`, `hass_000001/`, `system_002/`.
- The original `config.json` had a hybrid structure where TCS appeared both inside
  `gatewayInfo` and at the gateway level; normalised during migration.
- Migrated from `schemas_0` format.
