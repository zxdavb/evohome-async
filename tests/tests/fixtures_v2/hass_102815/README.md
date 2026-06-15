# fixtures_v2/hass_102815

Source: [Home Assistant core issue #102815](https://github.com/home-assistant/core/issues/102815)

## System

- Location: 4000016 (Belgium, synthesised ID — not in original)
- Gateway: 4000016 (synthesised)
- TCS: 632515
- 1 zone: DINING ROOM (632515)
- No DHW
- Timezone: `RomanceStandardTime` (UTC+01:00, Brussels)
- Device type: FocusProWifi (heat + cool)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000016, Belgium |
| `user_locations.json` | Migrated from `schemas_0/hass_102815/config.json`; PII replaced |

## Notes

- **Config-only fixture** — no status file in original report.
  Tests for this dir correctly xfail (`pytest.mark.xfail`).
- FocusProWifi with heating and cooling capability (`canControlCool: true`).
- Location ID and gateway ID are synthesised (original report had none); system/zone ID is real.
- Migrated from `schemas_0` format.
