# Lecture 9: Hash Tables

15-122 Principles of Imperative Computation · Fall 2026

## Announcements

Homework 4 is due Thursday at 9 pm. The midterm is in two weeks; a practice exam will be posted on Friday. Office hours move to GHC 5th floor this week only.

## Recap: the problem

Last lecture we needed a data structure supporting insert, lookup and delete by key. Sorted arrays give logarithmic lookup but linear insert; linked lists give constant insert but linear lookup. We want constant time for all three, on average.

## The idea

A hash function maps a key to an index in an array of fixed size. If two keys map to the same index we have a collision; the array slot holds a chain of entries, and a lookup walks the chain. If the hash function spreads keys evenly and the table is resized when the number of entries exceeds the number of slots, chains stay short and operations take constant expected time.

## Worked example

Insert the strings "cat", "act" and "dog" into a table of size 5 with the hash function that sums character codes modulo 5. "cat" and "act" have the same sum, so they land in the same slot and form a chain of length two; "dog" lands elsewhere. A lookup for "act" walks the first slot's chain and finds it at the second entry.

```
slot 0: dog
slot 1: 
slot 2: cat -> act
slot 3:
slot 4:
```

## What a good hash function needs

Two properties: it is cheap to compute, and it distributes real keys evenly across slots. The second property is the hard one; summing character codes fails it on anagrams, as the example shows. We will use a polynomial hash next lecture.

## Before next class

Read chapter 11 of the textbook and attempt exercise 11.3; we will start from its solution.

Slides based on material by the course staff. Not for redistribution.
