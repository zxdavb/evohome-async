# fixtures_v2/hass_179414

Source: [Home Assistant core issue #179414](https://github.com/home-assistant/core/issues/179414)
(upstream: [evohome-async issue #145](https://github.com/zxdavb/evohome-async/issues/145))

## System

**Wholly synthesised, pending the reporter's actual JSON**: the report included only the
error message. The shape is based on `hass_141882/` (a `Sydney` system, also in Australia).

- Location: 4001011 (Australia)
- Gateway: 4001012
- TCS: 4001013 — `modelType` of `Saratoga` (as reported)
- 1 zone: THERMOSTAT (4001014)
- No DHW
- Timezone: `AUSEasternStandardTime` (UTC+10:00, Sydney) — a guess: the report says only
  "Australia"

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised |
| `user_locations.json` | Synthesised |
| `status_4001011.json` | Synthesised |

## Notes

- Only the TCS `modelType` of `Saratoga` comes from the report. The rest (zones, system
  modes, setpoint capabilities, IDs) is synthesised.
- Zone 4001014 has a `modelType` of `NoSuchModelType` and a `zoneType` of `NoSuchZoneType`.
  These are deliberately not members of their `Tcc*` enums (and never will be), so that the
  vendor's enums being incomplete is exercised by the existing tests: each is passed
  through as a (snake_case) str, and logged as unknown. Do not "fix" them by adding them
  to the enums, as that would silently remove this coverage.
- When the reporter's JSON arrives, replace the synthesised data with it (per the PII
  policy), but keep a zone with these two unknown values, as `hass_178493/` does for its
  synthesised unknown fault type.
