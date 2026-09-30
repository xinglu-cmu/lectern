# lectern-cli

The Lectern engine and command-line tool. Full documentation, design and source: [github.com/xinglu-cmu/lectern](https://github.com/xinglu-cmu/lectern).

```bash
pip install lectern-cli
lectern scan assignment.pdf          # overview + zone map + findings
lectern scan assignment.pdf --json   # the full analysis, for scripts and agents
```

Works offline with `--no-llm`; an `ANTHROPIC_API_KEY` upgrades zoning quality and adds the overview.
