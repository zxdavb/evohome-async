# fixtures_v2/null_system_2

Synthesised fixture — null installation: a single location and gateway with no TCS.

## System

- Location: 4001006 (United Kingdom)
- Gateway: 4002006
- No TCS
- Timezone: `GMTStandardTime` (UTC+00:00)

The `null_system_*` fixtures each stop the location → gateway → TCS hierarchy at a
different level; this one stops at the gateway.

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000021, UK |
| `user_locations.json` | Synthesised — 1 location, 1 gateway, `temperatureControlSystems: []` |
| `status_4001006.json` | Synthesised — 1 gateway, `temperatureControlSystems: []` |

## Notes

- Replaces location 4001003 (`Schema No TCS`), formerly in `system_007/`.
