# fixtures_v2/hass_110065

Source: [Home Assistant core issue #110065](https://github.com/home-assistant/core/issues/110065)

## System

- Location: 4655156 (Belgium)
- Gateway: 4450182
- TCS: 6148217
- 6 zones: Living (6148216), Badkamer (6148370), Slaapkamer (6150627),
  Bryan (6150671), Katharina (6150691), (unnamed) (6248903)
- No DHW
- Timezone: `RomanceStandardTime` (UTC+01:00, Brussels)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000017, Belgium |
| `user_locations.json` | Migrated from `schemas_0/hass_110065/config.json`; PII replaced |
| `status_4655156.json` | From `schemas_0/hass_110065/status.json` |

## Notes

- Dutch zone names (Badkamer, Slaapkamer) in a `RomanceStandardTime` system confirm Belgium
  (Dutch-speaking, Brussels timezone).
- Zone 6248903 has an empty name in the original data.
- Migrated from `schemas_0` format.
