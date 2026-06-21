# fixtures_v2/hass_101355

Source: [Home Assistant core issue #101355](https://github.com/home-assistant/core/issues/101355)

## System

- Location: 1111111 (United Kingdom)
- Gateway: 2222222
- TCS: 3333333
- 1 zone: (unnamed) (7820586)
- No DHW
- Timezone: `GMTStandardTime` (UTC+00:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000013, UK |
| `user_locations.json` | Migrated from `schemas_0/hass_101355/config.json`; PII replaced |
| `status_1111111.json` | From `schemas_0/hass_101355/status.json` |
| `temperatures.json` | Temperature log from original report (informational) |

## Notes

- The original config had 1 zone; the status had 2 zones. `user_locations.json` uses the
  config (1 zone) and `status_1111111.json` uses the status (2 zones). The mismatch reflects
  the original report and is intentional — it tests that the library handles zone count
  differences between config and status gracefully.
- Location/gateway/system IDs (1111111, 2222222, 3333333) are likely placeholders.
- Migrated from `schemas_0` format.
