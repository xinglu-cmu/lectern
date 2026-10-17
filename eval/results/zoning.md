# Zoning accuracy results

30 labeled documents, 184 labeled segments (0 segments without a gold label, skipped).

| mode | accuracy | macro-F1 |
|---|---:|---:|
| heuristic-only | 0.85 | 0.89 |

Per zone (heuristic-only):

| zone | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| task | 0.76 | 0.89 | 0.82 | 38 |
| background | 0.92 | 0.83 | 0.87 | 93 |
| structure | 0.96 | 0.77 | 0.86 | 31 |
| example | 0.94 | 1.00 | 0.97 | 15 |
| ai_policy | 1.00 | 0.86 | 0.92 | 7 |
| unknown | 0.00 | 0.00 | 0.00 | 0 |

Confusion (rows = gold, columns = predicted, heuristic-only):

| gold \ pred | task | background | structure | example | ai_policy | unknown |
|---|---:|---:|---:|---:|---:|---:|
| task | 34 | 3 |  | 1 |  |  |
| background | 10 | 77 | 1 |  |  | 5 |
| structure | 1 | 3 | 24 |  |  | 3 |
| example |  |  |  | 15 |  |  |
| ai_policy |  | 1 |  |  | 6 |  |
| unknown |  |  |  |  |  |  |
