# tinycache 2.4 — Release Notes

Released 12 October 2026. Python 3.10 or newer. Install or upgrade with `pip install -U tinycache`.

This release is mostly about memory: the per-entry overhead is down by about a third, and the cache now reports its own size accurately instead of estimating it. There is one breaking change for people who subclassed `Cache`, described under Upgrading. Thanks to the fourteen people who filed issues or sent patches for this release.

## New

- `Cache.sizeof(key)` returns the measured size of an entry in bytes. Before 2.4 the size limit was enforced against an estimate that undercounted nested containers by up to 40 percent.
- A `on_evict` callback receives each entry as it leaves the cache, with the reason (`expired`, `size`, `explicit`). The callback runs synchronously, so keep it short.
- Type hints are complete and checked with mypy in strict mode.

## Fixed

- An entry whose time-to-live expired exactly on a clock tick could be returned once more before eviction. The comparison is now inclusive.
- `Cache.clear()` no longer holds the lock while calling `on_evict`, which could deadlock a callback that touched the cache.
- The README example for size limits used megabytes where the API takes bytes.

## Changed

- The default size limit is now 64 MB instead of unlimited. A cache that never set a limit will start evicting under memory pressure; set `max_bytes=None` to restore the old behaviour.

## Upgrading from 2.3

If you subclassed `Cache` and overrode `_evict`, rename your override to `_evict_one`: the old method now evicts in batches and calls the new one per entry. Run your tests after upgrading, and if you rely on the old unlimited default, pass `max_bytes=None` explicitly before deploying.

## Known issues

On Python 3.10 only, `sizeof` of an entry holding a `frozenset` returns zero. A fix is in review and will ship as 2.4.1.

Full changelog: https://example.org/tinycache/compare/2.3.2...2.4.0 · Report a problem: https://example.org/tinycache/issues
