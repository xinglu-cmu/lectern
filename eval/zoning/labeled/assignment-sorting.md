# Assignment 2: Sorting Algorithms

## Overview

In this assignment you will implement three sorting algorithms and compare their running time on random, sorted and reverse-sorted inputs. Sorting is one of the oldest problems in computer science, and the three algorithms here are the ones every standard library builds on. The goal is not the code, which is short, but the measurement: you should come away able to explain why an algorithm that is slower in theory can be faster in practice on small inputs.

## Background

A comparison sort can do no better than n log n comparisons in the worst case. Merge sort achieves that bound by splitting the input in half, sorting each half, and merging. Quicksort achieves it on average by partitioning around a pivot, but a bad pivot sequence degrades it to quadratic time. Bubble sort is quadratic always and is included as a baseline, because its inner loop is so simple that it wins on inputs of a dozen elements.

## Deliverables

1. Implement `bubble_sort`, `merge_sort` and `quick_sort` in `sort.py`. Each must sort a list in place and return the number of comparisons made.
2. Write a report of at most two pages with a table of running times for inputs of size 10, 100, 1,000 and 10,000, and one plot.
3. Submit `sort.py` and `report.pdf` on the course site by Friday at 11:59 pm.

Your code must run with Python 3.12 and no third-party packages. Late submissions lose 10% per day.

## Grading

Correctness on hidden tests is worth 60 points. The report is worth 40: 20 for the comparison, 10 for the plot, 10 for clarity.

## Policies

You may discuss ideas with classmates, but the code and the report must be your own. Use of generative AI tools such as ChatGPT to write code or text for this assignment is not permitted.

## Example

For the input `[3, 1, 2]`, bubble sort makes three comparisons and two swaps:

```
[3, 1, 2] -> [1, 3, 2] -> [1, 2, 3]
```

## References

- Cormen, Leiserson, Rivest and Stein. Introduction to Algorithms, chapter 2. https://example.org/clrs
- Knuth. The Art of Computer Programming, volume 3. https://example.org/taocp
