# fixtures_v2/default

Default v2 fixture — a representative UK system used as the primary test case and
schedule fallback for other systems.

## System

- Location: 2738909 (United Kingdom)
- Gateway: 2499896
- TCS: 3432522
- 9 zones: Dead Zone (3432521), Main Room (3432576), Front Room (3432577),
  Kitchen (3432578), Bathroom Dn (3432579), Main Bedroom (3432580),
  Kids Room (3449703), Bathroom Up (3449740), Spare Room (3450733)
- DHW: 3933910
- Timezone: `GMTStandardTime` (UTC+00:00)

## Files

| File | Source |
|------|--------|
| `user_account.json` | Synthesised — real userId 2263181, UK |
| `user_locations.json` | Synthesised — real IDs, placeholder personal fields |
| `status_2738909.json` | Synthesised — representative state |
| `schedule_zone.json` | Generic fallback schedule (used by all dirs without their own) |
| `schedule_dhw.json` | Generic DHW fallback schedule |

## Notes

- `schedule_zone.json` and `schedule_dhw.json` in this dir are the fallback used by the
  conftest for any zone/DHW in any fixture dir that doesn't have its own schedule file.
- v0 counterpart: `fixtures_v0/default/`
