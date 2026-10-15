# Zoning accuracy results

6 labeled documents, 35 labeled segments (0 segments without a gold label, skipped).

| mode | accuracy | macro-F1 |
|---|---:|---:|
| heuristic-only | 0.83 | 0.86 |

Per zone (heuristic-only):

| zone | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| task | 0.60 | 1.00 | 0.75 | 6 |
| background | 1.00 | 0.69 | 0.81 | 16 |
| structure | 1.00 | 0.86 | 0.92 | 7 |
| example | 0.67 | 1.00 | 0.80 | 4 |
| ai_policy | 1.00 | 1.00 | 1.00 | 2 |

Confusion (rows = gold, columns = predicted, heuristic-only):

| gold \ pred | task | background | structure | example | ai_policy |
|---|---:|---:|---:|---:|---:|
| task | 6 |  |  |  |  |
| background | 4 | 11 |  | 1 |  |
| structure |  |  | 6 | 1 |  |
| example |  |  |  | 4 |  |
| ai_policy |  |  |  |  | 2 |
