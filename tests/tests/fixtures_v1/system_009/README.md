# fixtures_v1/system_009

Captured from a real (dummy) account on 2026-10-16 — multiple locations (UK).

## System

- User: 2512649 (en-GB)
- Contains 3 locations (in this order, which differs from that of the v2 API):
  - `3164610` (`Living room`) — no devices (so no TCS)
  - `2738909` (`My Home`) — 1 zone, all with gateway `2499896`
  - `8380809` (`My Home (RFG100)`) — 1 zone and 1 DHW, all with gateway `2678129`

## Files

| File | Source |
|------|--------|
| `user_info.json` | `accountInfo`, wrapped in `{"userInfo": ...}`; PII replaced |
| `user_locs.json` | `locations?userId=2512649&allData=True`; PII replaced |
| `gateways_{loc_id}.json` | `gateways?locationId={loc_id}&allData=True` (`[]` for `3164610`); CRC replaced with `"0000"` |
| `weather_{loc_id}.json` | `weather/currentweather?locationId={loc_id}&language=en-GB` |
| `forecast_{loc_id}.json` | `weather/dailyforecast?locationId={loc_id}&days=3&language=en-GB` |

The library uses only `accountInfo` and `locations`; the other files are for future use.
They are documented (without response schemas) in the vendor's API reference
(`https://tccna.resideo.com/WebApi/Help/Reference`, after logging in with the
application id).

## Notes

- v2 counterpart: `fixtures_v2/system_009/` (the same account, captured at the same time)
- Each device's `macID` is that of its gateway (c.f. the `mac` of the gateway in
  `gateways_{loc_id}.json`, and of its v2 gateway).
- There are no v1 schedules: `schedule/{device_id}` (and `schedule?deviceId=`) returns
  `400 [{"code": "ScheduleNotSupported"}]` for every device (all have
  `"scheduleCapable": false`). See `fixtures_v2/system_009/` for their schedules.
- The `weather` of each location (in `user_locs.json`) is a summary of
  `weather_{loc_id}.json`; the v2 API has no known weather URL.
