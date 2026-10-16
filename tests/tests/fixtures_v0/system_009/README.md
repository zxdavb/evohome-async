# fixtures_v0/system_009

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

## Notes

- v2 counterpart: `fixtures_v2/system_009/` (the same account, captured at the same time)
- Each device's `macID` is that of its gateway (c.f. the `mac` of its v2 gateway).
