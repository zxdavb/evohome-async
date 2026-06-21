# fixtures_v2/hass_112884

Source: [Home Assistant core issue #112884](https://github.com/home-assistant/core/issues/112884)

## System

- Location: 2049339 (Netherlands)
- Gateway: 1710429
- TCS: 2069121
- 9 zones: Livingroom (2069120), Badkamer 1 (2069237), Gang (2069263),
  Washok (2297923), Badkamer 2 (2306137), Vloer (2306140), Balzaal (2329524),
  Logeerkamer (2329554), Slaapkamer (2329571)
- No DHW
- Timezone: `WEuropeStandardTime` (UTC+01:00, Amsterdam)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000019, Netherlands |
| `user_locations.json` | Migrated from `schemas_1/hass_112884/config.json`; PII replaced |
| `status_2049339.json` | From `schemas_1/hass_112884/status.json` |

## Notes

- Migrated from `schemas_1` format (had `locationId` and `gatewayId` but missing
  `mac`/`crc`/`isWiFi` and `useDaylightSaveSwitching`; added during migration).
- Dutch zone names confirm Netherlands.
