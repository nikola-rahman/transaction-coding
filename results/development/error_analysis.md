# Error analysis on development organizations, fixed history, two seeds

Development organizations only: the 1,000 fixed development rows and the held-out next-step sets, scored with history fixed at 1,000 transactions (before the switch to rolling history). The test councils were not used. Scripts: `src/error_analysis.py`, `src/error_retrieval.py`.

## Accounts
| Case | Rows | Top-1 | Top-5 |
|---|---|---|---|
| Easy | 302 | 94 | 97 |
| Thin | 166 | 84 | 92 |
| Several accounts | 213 | 56 | 78 |
| New merchant | 319 | 25 | 54 |

| Evidence | Rows | Top-1 | Top-5 |
|---|---|---|---|
| True account shown in history | 701 | 81.0 | 93.7 |
| Account used before, not via this merchant | 195 | 16.2 | 37.7 |
| Account never used in the past | 96 | 23.4 | 58.9 |
| In this merchant's past, not shown | 8 | 0.0 | 6.2 |

Retrieval is not the bottleneck. Near-duplicate account names cost about 2 points of top-1 (622 to 640-643 of 1,000; string-similarity heuristic, unchecked row by row).

## Wrong accepts at confidence 0.8 (22 rows, either seed)
| Group | Rows |
|---|---|
| Same vendor recoded, history points elsewhere | 7 |
| Same account under another name | 6 |
| Loan coded as incentive (Green Bank) | 4 |
| Purpose unknowable, new merchant | 3 |
| Large project-specific payment | 1 |
| Plain wrong guess | 1 |

## Calibration (pooled seeds)
| Confidence | Accuracy |
|---|---|
| Under 0.3 | 18.0 |
| 0.3-0.5 | 37.5 |
| 0.5-0.7 | 65.8 |
| 0.7-0.8 | 76.5 |
| 0.8-0.9 | 84.9 |
| 0.9-0.95 | 96.2 |
| 0.95+ | 99.3 |

## Gates (designed after reading these rows, so untested)
| Rule | Seed 1 | Seed 2 |
|---|---|---|
| Confidence 0.8 | 404 accepted, 19 wrong | 339, 13 |
| 0.8 + known merchant | 386, 14 | 325, 9 |
| 0.8 + known + amount within 2x | 381, 14 | 321, 9 |
| Confidence 0.9 | 351, 9 | 257, 2 |

## Actions
| Set | Strict | Lookup and document merged | Accept vs route |
|---|---|---|---|
| Real held | 78.8 / 81.2 | 85.2 / 86.1 | 90.0 / 90.6 |
| Hard held | 74.3 / 73.7 | 80.9 / 80.9 | 86.8 / 86.8 |
| Person held | 76.0 / 79.0 | 78.0 / 81.0 | 89.0 / 90.0 |

Model accepted where the labeller did not: 65 cases over two seeds and three sets; the top account was right in 49. Action probability 0.9+ is right about 96% of the time.

## Coded without asking, wrong, any confidence (79 unique rows across two seeds, read by hand)
| Group | Rows |
|---|---|
| Same account, different name | 20 |
| History shows one account, truth differs | 19 |
| New merchant, purpose or item unknowable | 16 |
| Several accounts in history, picked one | 11 |
| Wrong guess from the merchant name | 8 |
| Loan coded as incentive | 4 |
| Large project payment | 1 |

Groups are one reader's judgment.
