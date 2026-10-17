# Platform Team — Architecture Review, Thursday 22 October 2026

14:00–15:30 · Room 4B and video link · Chair: Dana Whitfield · Notes: rotating (this week: Sam)

## Why this meeting

We have three proposals that each touch the ledger's write path, and two of them conflict. Rather than review them one at a time and discover the conflict in implementation, this session puts them side by side and leaves with one decision on sequencing. Nothing is being approved for build; the output is an order and a list of open questions for each author.

## Before the meeting

Read all three proposals (links below; about 40 minutes in total) and add your questions as comments in the documents by Wednesday noon, so authors can prepare answers. If you cannot attend, send your position on the sequencing question to Dana by Wednesday evening; silence will be read as no objection.

## Agenda

1. Continuous settlement, phase 2 (Priya, 20 min): moving the remaining batch payouts onto the continuous path. Depends on the journal change in item 2.
2. Append-only journal for the ledger (Morgan, 25 min): replacing the row-level lock. The largest change of the three; carries the migration risk.
3. Idempotency keys at the API edge (Sam, 15 min): independent of the other two but shares the same tables, so the migrations must be ordered.
4. Sequencing decision (all, 20 min).
5. Open questions and owners (10 min).

## Context the authors assumed

The ledger processes about 15,000 writes a minute at peak, with a p99 commit latency of 95 ms since the journal prototype went in. The settlement batch runs at 02:00 UTC and takes 40 minutes. The migration freeze for the quarter-end is 14 December to 4 January; anything with a schema change has to land before it or wait.

## Parking lot

Items raised but out of scope for this session: observability of the new path, the on-call rotation for December, and the vendor review for the fraud model. These go to the fortnightly planning meeting.

Dial-in: +1 412 555 0100, code 884 112. The recording is kept for 30 days on the team drive.
