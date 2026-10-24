# Zoning accuracy results

68 labeled documents, 555 labeled segments (461 segments without a gold label, skipped).

| mode | accuracy | macro-F1 |
|---|---:|---:|
| heuristic-only | 0.70 | 0.75 |
| + LLM | 0.82 | 0.81 |
| delta | +0.12 | +0.06 |
| + local | 0.72 | 0.72 |
| delta | +0.01 | -0.03 |
| + distilled classifier | 0.77 | 0.78 |
| delta | +0.06 | +0.03 |

By document group (accuracy / macro-F1):

| mode | authored (30 docs, 184 segs) | real (38 docs, 371 segs) |
|---|---:|---:|
| heuristic-only | 0.85 / 0.88 | 0.63 / 0.62 |
| + LLM | 0.86 / 0.87 | 0.81 / 0.77 |
| + local | 0.80 / 0.82 | 0.68 / 0.62 |
| + distilled classifier | 0.86 / 0.88 | 0.72 / 0.67 |

Per zone (heuristic-only):

| zone | precision | recall | F1 | support |
|---|---:|---:|---:|---:|
| task | 0.57 | 0.75 | 0.65 | 107 |
| background | 0.84 | 0.65 | 0.73 | 226 |
| structure | 0.93 | 0.74 | 0.83 | 172 |
| example | 0.57 | 0.70 | 0.62 | 43 |
| ai_policy | 1.00 | 0.86 | 0.92 | 7 |
| unknown | 0.00 | 0.00 | 0.00 | 0 |

Confusion (rows = gold, columns = predicted, heuristic-only):

| gold \ pred | task | background | structure | example | ai_policy | unknown |
|---|---:|---:|---:|---:|---:|---:|
| task | 80 | 15 | 1 | 9 |  | 2 |
| background | 45 | 147 | 9 | 12 |  | 13 |
| structure | 8 | 9 | 128 | 2 |  | 25 |
| example | 8 | 3 |  | 30 |  | 2 |
| ai_policy |  | 1 |  |  | 6 |  |
| unknown |  |  |  |  |  |  |

Unlabeled segments (add a `match` to label them):

- real-article-wiki-rfi.html s3 (hidden): 'CentralNotice'
- real-article-wiki-rfi.html s5 (structure): 'Toggle the table of contents\n\n# Request for information\n\n8 l'
- real-article-wiki-rfi.html s6 (hidden): 'Business process'
- real-article-wiki-rfi.html s7 (structure): 'This article is about the business practice. For the motion '
- real-article-wiki-rfi.html s12 (hidden): 'NewPP limit report Parsed by mw‐web.eqiad.main‐597bd9c9c‐5kj'
- real-article-wiki-rfi.html s13 (hidden): 'Transclusion expansion time report (%,ms,calls,template) 100'
- real-article-wiki-rfi.html s14 (hidden): 'Render ID dd85565e-bcec-11f1-941c-fdc81723c778'
- real-article-wiki-rfi.html s15 (hidden): 'Saved in parser cache with key enwiki:parsoid-pcache:1089316'
- real-article-wiki-rfi.html s16 (hidden): 'Parsoid 0.24.0.0-alpha24'
- real-article-wiki-rfi.html s17 (hidden): 'Post‐processing cache key enwiki:postproc‐parsoid‐pcache:108'
- real-article-wiki-syllabus.html s3 (hidden): 'CentralNotice'
- real-article-wiki-syllabus.html s5 (structure): 'Toggle the table of contents\n\n# Syllabus\n\n35 languages\n\n- ال'
- real-article-wiki-syllabus.html s6 (hidden): 'Outline and summary of topics to be covered in an education '
- real-article-wiki-syllabus.html s12 (hidden): 'NewPP limit report Parsed by mw‐web.eqiad.main‐69f4bc958d‐6d'
- real-article-wiki-syllabus.html s13 (hidden): 'Transclusion expansion time report (%,ms,calls,template) 100'
- real-article-wiki-syllabus.html s14 (hidden): 'Render ID c02a643b-cf23-11f1-bf7b-432deb048c5f'
- real-article-wiki-syllabus.html s15 (hidden): 'Saved in parser cache with key enwiki:parsoid-pcache:1977285'
- real-article-wiki-syllabus.html s16 (hidden): 'Parsoid 0.24.0.0-alpha27'
- real-article-wiki-syllabus.html s17 (hidden): 'Post‐processing cache key enwiki:postproc‐parsoid‐pcache:197'
- real-article-wiki-syllabus.html s18 (structure): 'Retrieved from " https://en.wikipedia.org/w/index.php?title='
- real-assignment-cs50x-pset2.html s3 (hidden): 'Tools'
- real-assignment-cs50x-pset2.html s4 (structure): '- CS50.ai\n\n- Ed Discussion for Q&A\n\n- Visual Studio Code'
- real-assignment-cs50x-pset2.html s5 (hidden): 'Highlights'
- real-assignment-cs50x-pset2.html s6 (structure): '- CS50 Educator Workshop\n\n- CS50x Puzzle Day 2024\n\n- Gallery'
- real-assignment-cs50x-pset2.html s7 (hidden): 'Course Nav'
- real-assignment-cs50x-pset2.html s9 (hidden): 'Final project spec, seminars, shorts'
- real-assignment-cs50x-pset2.html s10 (structure): '- Final Project\n\n- Gallery of Final Projects 🖼️\n\n- Seminars\n'
- real-assignment-cs50x-pset2.html s11 (hidden): 'Items that might usually appear in an academic syllabus'
- real-assignment-cs50x-pset2.html s13 (hidden): 'Where to watch or take the class course'
- real-assignment-cs50x-pset2.html s14 (structure): '- Apple TV\n\n- edX\n\n- Google TV\n\n- Harvard Extension School\n\n'
