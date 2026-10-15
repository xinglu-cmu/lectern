# Programming Assignment 4: Graph Search

## Overview

In this assignment you will implement three graph-search algorithms and compare how many nodes each one expands on a set of maze-like grids. Graph search is the backbone of route planning, puzzle solving and many scheduling problems, and the three algorithms here (breadth-first search, uniform-cost search and A*) differ only in how they order the frontier. Understanding that one difference is the point of the exercise.

The starter code gives you a grid loader, a renderer and a test harness. You should not need to change them.

## Deliverables

1. Implement `bfs`, `ucs` and `astar` in `search.py`. Each function takes a grid and returns the path and the number of expanded nodes.
2. Write a short report (at most two pages) comparing the three algorithms on the five provided grids. Include one table and one plot.
3. Submit `search.py` and `report.pdf` through the course site by Friday, October 16 at 11:59 pm.

Late submissions lose 10% per day. Your code must run with Python 3.12 and no third-party packages.

## Grading

The autograder awards 60 points for correctness on hidden grids. The report is worth 40 points: 20 for the comparison, 10 for the plot, 10 for clarity. Partial credit is given for a correct path with a wrong expansion count.

## Policies

Discussing ideas with classmates is encouraged, but the code and the report must be your own. Use of generative AI tools to write code or text for this assignment is not permitted. If you used an AI tool for anything else, say so in the report.

## Example

For the 3x3 grid below, with S the start and G the goal and # a wall, breadth-first search expands 5 nodes and returns the path right, right, down, down.

    S . .
    # # .
    G . .
