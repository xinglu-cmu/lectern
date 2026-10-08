# tinycache

A small in-memory cache for Python with time-to-live and size limits, in one file with no dependencies.

[![ci](https://img.shields.io/badge/ci-passing-green)](https://example.org/ci) · [PyPI](https://example.org/pypi) · [Changelog](CHANGELOG.md)

## Why

Most projects that reach for a caching library need two things: entries that expire, and a cap on how many entries are kept. The big libraries do far more, and bring dependencies with them. tinycache does those two things in about two hundred lines, with the same `get` / `set` interface as a dictionary.

## Install

```
pip install tinycache
```

## Usage

```python
from tinycache import Cache

cache = Cache(max_size=1000, ttl_seconds=300)
cache.set("user:42", {"name": "Ada"})
cache.get("user:42")  # {'name': 'Ada'}
cache.get("missing", default=None)
```

Entries older than `ttl_seconds` are dropped on access; when the cache is full, the least recently used entry is evicted.

## Contributing

Open an issue before a large change. Run the tests with `pytest` and keep coverage above 95%. All contributions are accepted under the MIT license; by submitting a pull request you agree to that.

## License

MIT © 2026 Example Maintainers
