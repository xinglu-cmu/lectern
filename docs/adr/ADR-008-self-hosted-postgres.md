# ADR-008: Self-host Postgres in the VM's compose stack instead of Neon

**Status:** accepted · 2026-09-24 · replaces Neon in the deploy plan (DESIGN §10)

## Context

The deploy plan put Postgres on Neon's free tier. Neon bills compute in CU-hours and suspends a compute after 5 idle minutes; on the Free plan that scale-to-zero cannot be disabled, and compute is capped at 100 CU-hours per project per month. Lectern's worker is a polling consumer ([ADR-004](ADR-004-postgres-job-queue.md)): it queries the job table every few seconds, so the compute never reaches 5 idle minutes. At the minimum size (0.25 CU), an always-on compute uses 0.25 × 730 h ≈ 182 CU-hours a month. The Free allowance runs out around day 17 and the database is suspended for the rest of the month. On the Launch plan ($0.106 per CU-hour) the same usage costs about $19 a month, which is the whole infrastructure budget (< $20/month, DESIGN §2 G7) spent on one component. (Prices as of 2026-09.)

Options considered:

1. **Stay on Neon and make the worker idle-friendly.** Polling every few minutes delays every upload by up to that long. `LISTEN/NOTIFY` needs a held connection, which keeps the compute awake anyway. An API-to-worker wake-up call adds the runtime coupling [ADR-002](ADR-002-service-split.md) avoids.
2. **Pay for Neon Launch.** Works, at about $19 a month.
3. **Another managed free tier.** Different quotas, same exposure to a vendor's idle policy.
4. **Run Postgres in the compose stack on the VM** that already runs the api and worker.

## Decision

Option 4. Production runs the same `postgres:18` image as local development, in the VM's compose file, reachable only on the compose network (no published port; admin access through an SSH tunnel).

Backups: a nightly `pg_dump -Fc` streamed to R2, kept for 14 days by an R2 lifecycle rule, plus a scripted restore drill (restore the latest dump into a scratch container, run smoke queries) that runs at first deploy and after any change to the backup job.

Version: with Neon gone, nothing pins an older major. Postgres 18 is current (supported until 2030-11) and adds a built-in `uuidv7()` for time-ordered keys. Picking the major now, before any data exists, avoids a `pg_upgrade` later.

## Rationale

- Polling costs nothing on hardware already paid for, so ADR-004's queue design stays as it is.
- Co-location: the api, worker and database share one host, so there is no network hop to the database, no connection cap or pooler to manage, and no egress fee.
- Dev/prod parity: one image, one configuration, one set of extensions.
- Headroom: the CAX21 has 8 GB of RAM; this workload's Postgres needs a few hundred MB.

## Consequences

- We own backups, restores, minor-version updates (`docker compose pull`) and disk monitoring. A disk-usage alert joins the week-6 alert set.
- Recovery point objective is about 24 hours: losing the VM loses at most a day of writes. Uploads can be re-uploaded, and accounts and exports are small, so this is acceptable for v1. Recovery means a new VM plus a restore of the latest dump, following the drill's runbook.
- The production deploy gains a backup job and a restore runbook; Neon drops out of the account list.

## Revisit when

Real users depend on the data (then add WAL archiving to R2 with WAL-G or pgBackRest for point-in-time recovery, or move to a managed provider), or the deploy grows beyond one VM.
