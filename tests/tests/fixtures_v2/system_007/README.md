# fixtures_v2/system_007

Synthesised fixture — schema coverage for location/gateway/TCS combinations.

## System

Contains 4 locations to cover all config/status shape combinations:

- `4001001` (`Schema Maximal`) — 1 gateway, 1 TCS, 12 zones, 1 DHW
- `4001002` (`Schema Minimal`) — 1 gateway, 1 TCS, 1 zone, no DHW
- `4001003` (`Schema No TCS`) — 1 gateway, no TCS
- `4001004` (`Schema No Gateway`) — no gateways

Timezone for all locations: `GMTStandardTime`.

## Files

- `user_account.json`
- `user_locations.json`
- `status_4001001.json`
- `status_4001002.json`
- `status_4001003.json`
- `status_4001004.json`
