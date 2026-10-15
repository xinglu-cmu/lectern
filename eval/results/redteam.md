# Red-team suite results

Offline (`--no-llm`), deterministic corpus. Recall = attacked documents where an expected detector fired on the payload; precision counts the same detector family firing on clean controls.

| technique | attacked | detected | recall | precision | D1 also | quarantined |
|---|---:|---:|---:|---:|---:|---:|
| H1_white | 9 | 9 | 1.00 | 1.00 | 9 | 9 |
| H2_tiny | 6 | 6 | 1.00 | 1.00 | 6 | 6 |
| H3_offpage | 3 | 3 | 1.00 | 1.00 | 3 | 3 |
| H4_display | 3 | 3 | 1.00 | 1.00 | 3 | 3 |
| H4_offscreen | 3 | 3 | 1.00 | 1.00 | 3 | 3 |
| H4_comment | 3 | 3 | 1.00 | 1.00 | 3 | 3 |
| H4_vanish | 3 | 3 | 1.00 | 1.00 | 3 | 3 |
| H5_metadata | 9 | 9 | 1.00 | 1.00 | 0 | 9 |
| H6_tags | 9 | 9 | 1.00 | 1.00 | 9 | 9 |
| H6_zerowidth | 9 | 9 | 1.00 | 1.00 | 9 | 0 |
| D1_visible | 9 | 9 | 1.00 | 1.00 | 9 | 0 |

Controls: 9 clean documents; hidden-text findings on them: none.
