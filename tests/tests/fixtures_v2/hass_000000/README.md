# fixtures_v2/hass_000000

Source: Unknown

## System

- Location: 2738909 (United Kingdom)
- Gateway: 2499896
- TCS: 3432522
- 9 zones: Dead Zone (3432521), Main Room (3432576), Front Room (3432577),
  Kitchen (3432578), Bathroom Dn (3432579), Main Bedroom (3432580),
  Spare Room (3449703), Bathroom Up (3449740), Kids Room (3450733)
- No DHW
- Timezone: `GMTStandardTime` (UTC+00:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000008, UK |
| `user_locations.json` | Migrated from `schemas_0/hass_000000/config.json`; PII replaced |
| `status_2738909.json` | From `schemas_0/hass_000000/status.json` |
| `temperatures.json` | Temperature log from original report (informational) |

## Notes

- Same location/gateway/system IDs as `default/`, `hass_000001/`, `hass_000002/`, `system_002/`
  — all from the same physical installation with different reporters/states.
- Migrated from `schemas_0` format (had no `locationId` in `locationInfo`, no `gatewayInfo`).
