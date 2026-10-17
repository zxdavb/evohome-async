# fixtures_v2/system_009

Captured from a real (dummy) account on 2026-10-16 — multiple locations (UK).

## System

Contains 3 locations (in this order, which differs from that of the v1 API):

- `2738909` (`My Home`) — 1 gateway (`2499896`), 1 TCS (`3432522`), 1 zone, no DHW
- `3164610` (`Living room`) — no gateway (so no TCS)
- `8380809` (`My Home (RFG100)`) — 1 gateway (`2678129`), 1 TCS (`3744416`), 1 zone, 1 DHW

## Files

- `user_account.json`
- `user_locations.json`
- `status_2738909.json`, `status_3164610.json`, `status_8380809.json`
- `schedule_3432521.json`, `schedule_3744415.json` (zones), `schedule_6860918.json` (DHW)

## Notes

- v1 counterpart: `fixtures_v1/system_009/` (the same account, captured at the same time)
- The JSON is as returned by the vendor, except that personal fields (names, address,
  username) and CRCs (with `"0000"`) have been replaced; ids and MAC addresses are
  unaltered (the cross-API test compares the MACs).
