# Zoning accuracy results

15 labeled documents, 91 labeled segments (3 segments without a gold label, skipped).

| mode | accuracy | macro-F1 |
|---|---:|---:|
| heuristic-only | 0.87 | 0.91 |

Per zone (heuristic-only):

| zone | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| task | 0.83 | 0.83 | 0.83 | 18 |
| background | 0.89 | 0.82 | 0.86 | 40 |
| structure | 0.89 | 0.89 | 0.89 | 18 |
| example | 0.92 | 1.00 | 0.96 | 12 |
| ai_policy | 1.00 | 1.00 | 1.00 | 3 |
| unknown | 0.00 | 0.00 | 0.00 | 0 |

Confusion (rows = gold, columns = predicted, heuristic-only):

| gold \ pred | task | background | structure | example | ai_policy | unknown |
|---|---:|---:|---:|---:|---:|---:|
| task | 15 | 2 | 1 |  |  |  |
| background | 3 | 33 | 1 | 1 |  | 2 |
| structure |  | 2 | 16 |  |  |  |
| example |  |  |  | 12 |  |  |
| ai_policy |  |  |  |  | 3 |  |
| unknown |  |  |  |  |  |  |

Unlabeled segments (add a `match` to label them):

- email-meeting.md s1 (task): '# Re: Q4 planning review — agenda and what I need from you\n\n'
- minutes-board.md s6 (unknown): '## 5. Any other business\n\n- T. Brennan asked whether the boa'
- readme-library.md s1 (unknown): '# tinycache\n\nA small in-memory cache for Python with time-to'
