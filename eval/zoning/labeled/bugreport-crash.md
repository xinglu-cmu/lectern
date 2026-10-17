# tinycache crashes on eviction when an entry holds a generator (#412)

Opened by r-lindqvist · Labels: bug, 2.4 · Milestone: 2.4.1

## Summary

Since upgrading to 2.4.0, a cache with a size limit crashes with a `TypeError` the first time it evicts an entry whose value is a generator object. The same code ran for months on 2.3.2. I think the new `sizeof` measurement is walking into the generator.

## Environment

tinycache 2.4.0 · Python 3.12.4 · macOS 15.1 and Ubuntu 24.04 (same result on both) · installed from PyPI with pip 25.1.

## Steps to reproduce

```
from tinycache import Cache

c = Cache(max_bytes=1024)
c.set("gen", (i for i in range(10)))
c.set("big", "x" * 2048)   # forces an eviction
```

## Expected

The generator entry is evicted (or the oversized entry is rejected) and no exception is raised, as in 2.3.2.

## Actual

```
Traceback (most recent call last):
  File "repro.py", line 5, in <module>
    c.set("big", "x" * 2048)
  File "tinycache/cache.py", line 211, in set
    self._evict_one(victim)
  File "tinycache/cache.py", line 263, in _evict_one
    size = sizeof(entry.value)
  File "tinycache/size.py", line 40, in sizeof
    for item in obj:
TypeError: cannot measure a generator; it would be consumed
```

## Notes

Pinning to 2.3.2 avoids the problem. Setting `max_bytes=None` also avoids it, at the cost of the limit. I had a look at `size.py`: `sizeof` iterates anything with `__iter__`, which includes generators; checking for `__len__` first would skip them. Happy to send a patch if that is the direction you want.
