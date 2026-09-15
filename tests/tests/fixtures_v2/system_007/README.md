# fixtures_v2/system_007

Synthesised fixture — schema coverage for location/gateway/TCS combinations.

## System

Contains 2 locations to cover the config/status shapes of a populated TCS:

- `4001001` (`Schema Maximal`) — 1 gateway, 1 TCS, 12 zones, 1 DHW, `GMTStandardTime`
- `4001002` (`Schema Minimal`) — 1 gateway, 1 TCS, 1 zone, no DHW, `RomanceStandardTime`

The timezone is distinct for each location.

Sparse shapes (no gateway, no TCS) are covered by `null_system_1/` and `null_system_2/`,
which replace the former locations `4001004` and `4001003` of this fixture.

## Files

- `user_account.json`
- `user_locations.json`
- `status_4001001.json`
- `status_4001002.json`
