# fixtures_v2/hass_099625

Source: [Home Assistant core issue #99625](https://github.com/home-assistant/core/issues/99625)

## System

- Location: 4000014 (Finland, synthesised ID — not in original)
- Gateway: 4000014 (synthesised)
- TCS: 8557535
- 2 zones: Thermostat (8557539), Thermostat 2 (8557541)
- No DHW
- Timezone: `FLEStandardTime` (UTC+02:00, Helsinki)
- Device type: RoundWireless

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000014, Finland |
| `user_locations.json` | Migrated from `schemas_0/hass_099625/config.json`; PII replaced |

## Notes

- **Config-only fixture** — no status file in original report.
  Tests for this dir correctly xfail (`pytest.mark.xfail`).
- Location ID and gateway ID are synthesised (original report had none); system/zone IDs are real.
- Migrated from `schemas_0` format.
