# Why Your Cache Hit Rate Is Lying to You

Home | Blog | About | Subscribe

Most teams watch one number for their cache: the hit rate. Ninety-five percent sounds excellent. But a hit rate tells you how often the cache answered, not how much time it saved, and those two things come apart more often than you would think.

## The hot-key problem

Imagine a cache in front of a database where one key is read ten thousand times a second and a million other keys are read once a minute. Caching the one hot key gets you a hit rate near 100% while the database still serves a million slow queries a minute. The hit rate is honest about requests and silent about cost.

## What to measure instead

Measure the time saved: for each request, the latency of the backing store minus the latency of the cache, summed over a window. A cache that saves ten seconds of database time per second of wall clock is doing more than one that saves one, whatever their hit rates say. Most monitoring systems can compute this from two histograms you probably already collect.

## A worked example

Suppose the database answers in 20 ms and the cache in 1 ms. A 95% hit rate on 1,000 requests saves 950 × 19 ms, about 18 seconds. Now suppose the misses are the expensive queries at 200 ms each: the 50 misses cost 10 seconds, and the real question is whether those 50 could be cached at all.

## Related posts

- How we cut our p99 in half
- Monitoring that pays for itself

© 2026 Example Engineering Blog. All rights reserved. Privacy policy · Terms
