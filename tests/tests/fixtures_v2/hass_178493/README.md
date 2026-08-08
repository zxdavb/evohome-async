# fixtures_v2/hass_178493

Source: [Home Assistant core issue #178493](https://github.com/home-assistant/core/issues/178493)

## System

- Location: 6557787 (Netherlands)
- Gateway: 6208789
- TCS: 8419116 (EvoTouch)
- 5 zones: Woonkamer (8419115), Badkamer (8419159), Kantoor (8419160),
  Slaapkamer (8419161), Zolder (8419162)
- No DHW
- Timezone: `WEuropeStandardTime` (UTC+01:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | From original report (redacted) |
| `user_locations.json` | From original report (redacted) |
| `status_6557787.json` | From original report |

## Notes

- The reason for this fixture: the TCS reports an active fault of
  `BoilerServiceRequired`, which was absent from `TccFaultType`. The schema rejected
  the whole location status, so the integration could not load at all.
- Two zone faults are also present on 8419162 (`TempZoneActuatorLowBattery` and
  `TempZoneSensorLowBattery`), exercising multiple active faults on one entity.
- The report arrived pre-redacted by the reporter, with masks that preserved the
  length of the original strings (e.g. `"Ju******************"`). These were replaced
  with masked synthesised values per the PII policy in the parent README; `mac`/`crc`
  were zero-filled, and the timezone `displayName` (not PII) was restored to its real
  value, having been masked in the original report.
