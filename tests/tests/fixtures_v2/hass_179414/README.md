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
- The zone's `modelType` of `FocusProWifiRetail` and `zoneType` of `Thermostat` are
  placeholders, as used by the other Australian non-evohome systems (`hass_094805/`,
  `hass_118169/`). The reporter's real zone may well differ.
- When the reporter's JSON arrives, replace the synthesised data with it (per the PII
  policy).
- Coverage of unknown enum values is in `system_009/`, not here.
