# fixtures_v2/null_system_1

Synthesised fixture — null installation: a single location with no gateways.

## System

- Location: 4001005 (United Kingdom)
- No gateways
- Timezone: `GMTStandardTime` (UTC+00:00)

The `null_system_*` fixtures each stop the location → gateway → TCS hierarchy at a
different level; this one stops at the location.

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — userId 4000020, UK |
| `user_locations.json` | Synthesised — 1 location, `gateways: []` |
| `status_4001005.json` | Synthesised — `gateways: []` |

## Notes

- Replaces location 4001004 (`Schema No Gateway`), formerly in `system_007/`.
