# Measuring Reading Order Errors in PDF Text Extraction

## Abstract

Text extraction from PDF files is a routine step in document pipelines, yet the order in which extracted text appears is rarely evaluated. We introduce a small benchmark of 120 two-column research pages with hand-verified reading order and measure three widely used extractors against it. We find that column interleaving affects between 4% and 19% of lines depending on the tool, and that errors concentrate around figures and footnotes.

## Introduction

Most document understanding systems begin by converting a PDF to text. Downstream tasks such as summarization and classification assume that the text reads in the order a person would read it. When columns are interleaved, sentences from different paragraphs are spliced together, and the damage is silent: the output is still fluent-looking text. Prior work has studied extraction accuracy at the character level; reading order has received less attention.

## Method

We selected 120 pages from open-access papers across four fields, chose pages with two columns and at least one figure, and recorded the correct line order by hand. Each extractor was run with default settings. We report the share of lines that appear out of order relative to the gold sequence, and we break the figure down by the position of the nearest figure or footnote.

## Results

Interleaving rates were 4.1%, 11.7% and 18.9% for the three extractors. Errors were three times more frequent on lines adjacent to a figure caption. Footnotes were appended to the wrong column in 27% of pages for the weakest tool.

## Discussion

Reading order is a measurable property and worth reporting alongside character accuracy. We release the benchmark so that extractor changes can be tracked over time. A limitation of this study is its focus on two-column layouts; single-column and tabular pages likely behave differently.

## References

Smith, J. and Lee, K. (2024). Layout analysis for scholarly documents. Proceedings of DocEng.
Garcia, M. (2023). A survey of PDF text extraction tools. Journal of Document Processing, 12(3).
