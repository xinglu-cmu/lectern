# CS 2110 — Take-Home Midterm

Released Monday 19 October 2026, 09:00 · Due Wednesday 21 October 2026, 23:59 · 100 points

## Instructions

Answer all four questions. Write your answers in a single PDF, one question per page, with your name and student id at the top of each page. Show your work: a correct final answer with no derivation earns at most half credit. Submit through the course site before the deadline; late submissions lose 10 points per hour.

## Collaboration and AI policy

This is an individual exam. You may consult the textbook, the lecture slides and your own notes. You may not discuss the questions with anyone other than the course staff until grades are released. The use of generative AI tools, including chat assistants and code completion, is not permitted on this exam; answers produced with such tools will be treated as academic dishonesty.

## Question 1 (20 points)

Give a tight asymptotic bound on the running time of the following function and justify it with a recurrence.

```
def f(n):
    if n <= 1:
        return 1
    return f(n // 2) + f(n // 2) + n
```

## Question 2 (30 points)

The table shows measured running times of a sorting routine. Determine which of the standard algorithms it is most likely to be, and explain which observations support and which contradict your answer.

| n | time (ms) |
|---|---|
| 1,000 | 2 |
| 10,000 | 26 |
| 100,000 | 310 |
| 1,000,000 | 3,700 |

## Question 3 (25 points)

Prove that any comparison-based algorithm that finds both the minimum and the maximum of n elements needs at least 3n/2 − 2 comparisons in the worst case.

## Question 4 (25 points)

Design a data structure that supports insert, delete and "report the median" in O(log n) time each. Describe the structure, give the three operations, and argue the bound.

Honor pledge: I affirm that this submission is my own work and that I have followed the collaboration and AI policy above. Signature: ____________ Date: ____________
