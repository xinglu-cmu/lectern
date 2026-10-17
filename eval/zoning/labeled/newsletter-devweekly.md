# Dev Weekly — Issue 142

View this email in your browser · [Archive](https://example.org/archive) · [Sponsor](https://example.org/sponsor)

Hello again. This week's issue is a little shorter than usual because half the editorial team was at a conference, and the other half was fixing the newsletter's own build after a dependency update broke the template renderer. The irony was not lost on us.

## What caught our eye

**Postgres 18 ships asynchronous I/O.** The headline feature of the new release is an I/O subsystem that issues reads ahead of the executor, which the release notes claim doubles sequential scan throughput on cloud block storage. Early benchmarks from two independent teams land between 1.4× and 2.1×, so the claim is holding up. Upgrades from 16 and 17 need a dump and restore of extension catalogs in a few edge cases; the migration guide lists them.

**A quieter month for JavaScript runtimes.** Bun and Deno both shipped point releases focused on compatibility rather than speed, which several maintainers read as both projects conceding that Node's module semantics are the standard to match. Node itself moved its type-stripping flag out of experimental status.

**The ACM study on AI-assisted code review.** A controlled study with 120 reviewers found that model-generated review comments were accepted at the same rate as human ones but caught fewer design-level problems and more style ones. The authors argue the tools should be positioned as a first pass, not a replacement.

## Reader challenge

Last issue's challenge, a lock-free queue in under 60 lines, drew 31 entries. The winning entry used a sequence-number ring buffer and is linked below. This week's challenge: write a rate limiter that is correct across process restarts. Send your entry to challenge@example.org by Friday with the subject line "Issue 142", and tell us which language you used and why. The best three are published next week.

## Jobs

Harbor Pay is hiring a backend engineer for its payments platform in Pittsburgh. A climate-data startup in Oslo is looking for a data engineer comfortable with Parquet and Arrow. Both listings are on the jobs page.

---

You are receiving this because you signed up at example.org. [Unsubscribe](https://example.org/unsubscribe) · [Update preferences](https://example.org/prefs) · Dev Weekly, PO Box 112, Portland, OR. © 2026 Dev Weekly LLC. All rights reserved.
