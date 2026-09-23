# Routing opportunity analysis: groq-gpt-oss-20b vs groq-gpt-oss-120b

104 total benchmark tasks. 75 have real ground truth for both models (exact_match/classification_label/valid_json, or the sandboxed code-execution grader). 29 remain ungraded (evaluation_type=manual, no grader exists yet).

## Full per-task, per-model breakdown

| task_id | category | difficulty | model | quality | latency_ms | nominal_cost_usd |
|---|---|---|---|---|---|---|
| classification-001 | classification | easy | groq-gpt-oss-20b | correct | 215 | 0.000019 |
| classification-001 | classification | easy | groq-gpt-oss-120b | correct | 403 | 0.000034 |
| classification-002 | classification | medium | groq-gpt-oss-20b | correct | 350 | 0.000023 |
| classification-002 | classification | medium | groq-gpt-oss-120b | correct | 469 | 0.000043 |
| classification-003 | classification | easy | groq-gpt-oss-20b | correct | 450 | 0.000020 |
| classification-003 | classification | easy | groq-gpt-oss-120b | correct | 458 | 0.000054 |
| classification-004 | classification | medium | groq-gpt-oss-20b | correct | 444 | 0.000025 |
| classification-004 | classification | medium | groq-gpt-oss-120b | correct | 456 | 0.000057 |
| classification-005 | classification | hard | groq-gpt-oss-20b | correct | 689 | 0.000030 |
| classification-005 | classification | hard | groq-gpt-oss-120b | correct | 417 | 0.000062 |
| classification-006 | classification | medium | groq-gpt-oss-20b | correct | 354 | 0.000022 |
| classification-006 | classification | medium | groq-gpt-oss-120b | correct | 372 | 0.000059 |
| classification-007 | classification | medium | groq-gpt-oss-20b | correct | 419 | 0.000035 |
| classification-007 | classification | medium | groq-gpt-oss-120b | correct | 721 | 0.000052 |
| classification-008 | classification | medium | groq-gpt-oss-20b | correct | 689 | 0.000043 |
| classification-008 | classification | medium | groq-gpt-oss-120b | correct | 1490 | 0.000062 |
| classification-009 | classification | easy | groq-gpt-oss-20b | correct | 286 | 0.000019 |
| classification-009 | classification | easy | groq-gpt-oss-120b | correct | 465 | 0.000060 |
| classification-010 | classification | medium | groq-gpt-oss-20b | incorrect | 298 | 0.000019 |
| classification-010 | classification | medium | groq-gpt-oss-120b | incorrect | 556 | 0.000067 |
| classification-011 | classification | hard | groq-gpt-oss-20b | correct | 313 | 0.000023 |
| classification-011 | classification | hard | groq-gpt-oss-120b | correct | 1097 | 0.000052 |
| classification-012 | classification | hard | groq-gpt-oss-20b | incorrect | 444 | 0.000040 |
| classification-012 | classification | hard | groq-gpt-oss-120b | correct | 596 | 0.000065 |
| classification-013 | classification | hard | groq-gpt-oss-20b | correct | 352 | 0.000034 |
| classification-013 | classification | hard | groq-gpt-oss-120b | correct | 652 | 0.000065 |
| coding-001 | coding | medium | groq-gpt-oss-20b | correct | 943 | 0.000145 |
| coding-001 | coding | medium | groq-gpt-oss-120b | correct | 1475 | 0.000340 |
| coding-002 | coding | easy | groq-gpt-oss-20b | correct | 548 | 0.000096 |
| coding-002 | coding | easy | groq-gpt-oss-120b | correct | 1037 | 0.000217 |
| coding-003 | coding | medium | groq-gpt-oss-20b | correct | 1152 | 0.000164 |
| coding-003 | coding | medium | groq-gpt-oss-120b | correct | 1417 | 0.000307 |
| coding-004 | coding | hard | groq-gpt-oss-20b | correct | 1062 | 0.000157 |
| coding-004 | coding | hard | groq-gpt-oss-120b | correct | 1358 | 0.000327 |
| coding-005 | coding | medium | groq-gpt-oss-20b | correct | 972 | 0.000177 |
| coding-005 | coding | medium | groq-gpt-oss-120b | correct | 1556 | 0.000388 |
| coding-006 | coding | easy | groq-gpt-oss-20b | correct | 888 | 0.000118 |
| coding-006 | coding | easy | groq-gpt-oss-120b | correct | 1559 | 0.000363 |
| coding-007 | coding | medium | groq-gpt-oss-20b | correct | 1392 | 0.000258 |
| coding-007 | coding | medium | groq-gpt-oss-120b | correct | 1466 | 0.000319 |
| coding-008 | coding | medium | groq-gpt-oss-20b | correct | 1158 | 0.000258 |
| coding-008 | coding | medium | groq-gpt-oss-120b | correct | 1851 | 0.000342 |
| coding-009 | coding | hard | groq-gpt-oss-20b | correct | 995 | 0.000202 |
| coding-009 | coding | hard | groq-gpt-oss-120b | correct | 1884 | 0.000466 |
| coding-010 | coding | hard | groq-gpt-oss-20b | correct | 897 | 0.000216 |
| coding-010 | coding | hard | groq-gpt-oss-120b | correct | 2605 | 0.000629 |
| coding-011 | coding | medium | groq-gpt-oss-20b | correct | 781 | 0.000119 |
| coding-011 | coding | medium | groq-gpt-oss-120b | correct | 2520 | 0.000630 |
| coding-012 | coding | hard | groq-gpt-oss-20b | correct | 937 | 0.000183 |
| coding-012 | coding | hard | groq-gpt-oss-120b | correct | 1870 | 0.000445 |
| coding-013 | coding | easy | groq-gpt-oss-20b | correct | 709 | 0.000162 |
| coding-013 | coding | easy | groq-gpt-oss-120b | correct | 1069 | 0.000235 |
| debugging-001 | debugging | hard | groq-gpt-oss-20b | not_evaluated | 914 | 0.000152 |
| debugging-001 | debugging | hard | groq-gpt-oss-120b | not_evaluated | 1296 | 0.000277 |
| debugging-002 | debugging | medium | groq-gpt-oss-20b | not_evaluated | 1185 | 0.000261 |
| debugging-002 | debugging | medium | groq-gpt-oss-120b | not_evaluated | 1703 | 0.000445 |
| debugging-003 | debugging | easy | groq-gpt-oss-20b | not_evaluated | 1133 | 0.000237 |
| debugging-003 | debugging | easy | groq-gpt-oss-120b | not_evaluated | 2518 | 0.000387 |
| debugging-004 | debugging | hard | groq-gpt-oss-20b | not_evaluated | 1029 | 0.000183 |
| debugging-004 | debugging | hard | groq-gpt-oss-120b | not_evaluated | 1958 | 0.000377 |
| debugging-005 | debugging | medium | groq-gpt-oss-20b | not_evaluated | 940 | 0.000192 |
| debugging-005 | debugging | medium | groq-gpt-oss-120b | not_evaluated | 1915 | 0.000511 |
| debugging-006 | debugging | easy | groq-gpt-oss-20b | not_evaluated | 844 | 0.000176 |
| debugging-006 | debugging | easy | groq-gpt-oss-120b | not_evaluated | 1479 | 0.000323 |
| debugging-007 | debugging | medium | groq-gpt-oss-20b | not_evaluated | 1580 | 0.000314 |
| debugging-007 | debugging | medium | groq-gpt-oss-120b | not_evaluated | 2292 | 0.000570 |
| debugging-008 | debugging | medium | groq-gpt-oss-20b | not_evaluated | 977 | 0.000210 |
| debugging-008 | debugging | medium | groq-gpt-oss-120b | not_evaluated | 2378 | 0.000606 |
| debugging-009 | debugging | hard | groq-gpt-oss-20b | correct | 1371 | 0.000283 |
| debugging-009 | debugging | hard | groq-gpt-oss-120b | correct | 2178 | 0.000545 |
| debugging-010 | debugging | hard | groq-gpt-oss-20b | correct | 710 | 0.000145 |
| debugging-010 | debugging | hard | groq-gpt-oss-120b | correct | 1242 | 0.000312 |
| debugging-011 | debugging | medium | groq-gpt-oss-20b | correct | 2264 | 0.000282 |
| debugging-011 | debugging | medium | groq-gpt-oss-120b | correct | 1762 | 0.000418 |
| debugging-012 | debugging | hard | groq-gpt-oss-20b | correct | 1696 | 0.000317 |
| debugging-012 | debugging | hard | groq-gpt-oss-120b | correct | 1872 | 0.000446 |
| debugging-013 | debugging | medium | groq-gpt-oss-20b | correct | 732 | 0.000142 |
| debugging-013 | debugging | medium | groq-gpt-oss-120b | correct | 1041 | 0.000233 |
| extraction-001 | extraction | easy | groq-gpt-oss-20b | correct | 509 | 0.000031 |
| extraction-001 | extraction | easy | groq-gpt-oss-120b | correct | 455 | 0.000063 |
| extraction-002 | extraction | medium | groq-gpt-oss-20b | correct | 478 | 0.000049 |
| extraction-002 | extraction | medium | groq-gpt-oss-120b | incorrect | 356 | 0.000048 |
| extraction-003 | extraction | easy | groq-gpt-oss-20b | correct | 854 | 0.000064 |
| extraction-003 | extraction | easy | groq-gpt-oss-120b | correct | 1267 | 0.000234 |
| extraction-004 | extraction | medium | groq-gpt-oss-20b | incorrect | 733 | 0.000087 |
| extraction-004 | extraction | medium | groq-gpt-oss-120b | incorrect | 996 | 0.000173 |
| extraction-005 | extraction | hard | groq-gpt-oss-20b | correct | 1055 | 0.000211 |
| extraction-005 | extraction | hard | groq-gpt-oss-120b | incorrect | 737 | 0.000139 |
| extraction-006 | extraction | easy | groq-gpt-oss-20b | correct | 896 | 0.000126 |
| extraction-006 | extraction | easy | groq-gpt-oss-120b | correct | 503 | 0.000088 |
| extraction-007 | extraction | medium | groq-gpt-oss-20b | correct | 405 | 0.000036 |
| extraction-007 | extraction | medium | groq-gpt-oss-120b | correct | 670 | 0.000065 |
| extraction-008 | extraction | easy | groq-gpt-oss-20b | incorrect | 318 | 0.000045 |
| extraction-008 | extraction | easy | groq-gpt-oss-120b | correct | 638 | 0.000082 |
| extraction-009 | extraction | medium | groq-gpt-oss-20b | correct | 441 | 0.000028 |
| extraction-009 | extraction | medium | groq-gpt-oss-120b | correct | 420 | 0.000040 |
| extraction-010 | extraction | hard | groq-gpt-oss-20b | correct | 371 | 0.000046 |
| extraction-010 | extraction | hard | groq-gpt-oss-120b | correct | 359 | 0.000067 |
| extraction-011 | extraction | hard | groq-gpt-oss-20b | correct | 569 | 0.000049 |
| extraction-011 | extraction | hard | groq-gpt-oss-120b | correct | 603 | 0.000081 |
| extraction-012 | extraction | medium | groq-gpt-oss-20b | incorrect | 409 | 0.000030 |
| extraction-012 | extraction | medium | groq-gpt-oss-120b | correct | 726 | 0.000058 |
| extraction-013 | extraction | hard | groq-gpt-oss-20b | correct | 446 | 0.000037 |
| extraction-013 | extraction | hard | groq-gpt-oss-120b | correct | 562 | 0.000074 |
| math-001 | math | easy | groq-gpt-oss-20b | correct | 285 | 0.000022 |
| math-001 | math | easy | groq-gpt-oss-120b | correct | 542 | 0.000035 |
| math-002 | math | hard | groq-gpt-oss-20b | correct | 526 | 0.000022 |
| math-002 | math | hard | groq-gpt-oss-120b | correct | 2365 | 0.000036 |
| math-003 | math | easy | groq-gpt-oss-20b | correct | 243 | 0.000019 |
| math-003 | math | easy | groq-gpt-oss-120b | correct | 486 | 0.000033 |
| math-004 | math | medium | groq-gpt-oss-20b | correct | 414 | 0.000020 |
| math-004 | math | medium | groq-gpt-oss-120b | correct | 317 | 0.000035 |
| math-005 | math | hard | groq-gpt-oss-20b | incorrect | 316 | 0.000019 |
| math-005 | math | hard | groq-gpt-oss-120b | incorrect | 446 | 0.000037 |
| math-006 | math | hard | groq-gpt-oss-20b | correct | 457 | 0.000032 |
| math-006 | math | hard | groq-gpt-oss-120b | correct | 565 | 0.000042 |
| math-007 | math | medium | groq-gpt-oss-20b | correct | 445 | 0.000033 |
| math-007 | math | medium | groq-gpt-oss-120b | correct | 544 | 0.000040 |
| math-008 | math | medium | groq-gpt-oss-20b | correct | 348 | 0.000026 |
| math-008 | math | medium | groq-gpt-oss-120b | correct | 515 | 0.000050 |
| math-009 | math | medium | groq-gpt-oss-20b | correct | 369 | 0.000037 |
| math-009 | math | medium | groq-gpt-oss-120b | correct | 608 | 0.000071 |
| math-010 | math | medium | groq-gpt-oss-20b | correct | 250 | 0.000030 |
| math-010 | math | medium | groq-gpt-oss-120b | correct | 441 | 0.000050 |
| math-011 | math | hard | groq-gpt-oss-20b | correct | 547 | 0.000034 |
| math-011 | math | hard | groq-gpt-oss-120b | incorrect | 562 | 0.000047 |
| math-012 | math | hard | groq-gpt-oss-20b | correct | 645 | 0.000082 |
| math-012 | math | hard | groq-gpt-oss-120b | correct | 937 | 0.000103 |
| math-013 | math | hard | groq-gpt-oss-20b | incorrect | 411 | 0.000032 |
| math-013 | math | hard | groq-gpt-oss-120b | incorrect | 1403 | 0.000043 |
| reasoning-001 | reasoning | medium | groq-gpt-oss-20b | not_evaluated | 575 | 0.000074 |
| reasoning-001 | reasoning | medium | groq-gpt-oss-120b | not_evaluated | 849 | 0.000110 |
| reasoning-002 | reasoning | easy | groq-gpt-oss-20b | not_evaluated | 1182 | 0.000232 |
| reasoning-002 | reasoning | easy | groq-gpt-oss-120b | not_evaluated | 2428 | 0.000629 |
| reasoning-003 | reasoning | medium | groq-gpt-oss-20b | not_evaluated | 1022 | 0.000223 |
| reasoning-003 | reasoning | medium | groq-gpt-oss-120b | not_evaluated | 1606 | 0.000353 |
| reasoning-004 | reasoning | hard | groq-gpt-oss-20b | not_evaluated | 555 | 0.000100 |
| reasoning-004 | reasoning | hard | groq-gpt-oss-120b | not_evaluated | 1111 | 0.000231 |
| reasoning-005 | reasoning | medium | groq-gpt-oss-20b | not_evaluated | 829 | 0.000187 |
| reasoning-005 | reasoning | medium | groq-gpt-oss-120b | not_evaluated | 1582 | 0.000313 |
| reasoning-006 | reasoning | easy | groq-gpt-oss-20b | not_evaluated | 1311 | 0.000213 |
| reasoning-006 | reasoning | easy | groq-gpt-oss-120b | not_evaluated | 1810 | 0.000424 |
| reasoning-007 | reasoning | medium | groq-gpt-oss-20b | correct | 961 | 0.000155 |
| reasoning-007 | reasoning | medium | groq-gpt-oss-120b | correct | 721 | 0.000165 |
| reasoning-008 | reasoning | medium | groq-gpt-oss-20b | correct | 696 | 0.000134 |
| reasoning-008 | reasoning | medium | groq-gpt-oss-120b | correct | 861 | 0.000166 |
| reasoning-009 | reasoning | hard | groq-gpt-oss-20b | not_evaluated | 1374 | 0.000241 |
| reasoning-009 | reasoning | hard | groq-gpt-oss-120b | not_evaluated | 2354 | 0.000554 |
| reasoning-010 | reasoning | hard | groq-gpt-oss-20b | correct | 1066 | 0.000208 |
| reasoning-010 | reasoning | hard | groq-gpt-oss-120b | correct | 1373 | 0.000298 |
| reasoning-011 | reasoning | medium | groq-gpt-oss-20b | correct | 653 | 0.000119 |
| reasoning-011 | reasoning | medium | groq-gpt-oss-120b | correct | 758 | 0.000124 |
| reasoning-012 | reasoning | hard | groq-gpt-oss-20b | not_evaluated | 1263 | 0.000286 |
| reasoning-012 | reasoning | hard | groq-gpt-oss-120b | not_evaluated | 2705 | 0.000635 |
| reasoning-013 | reasoning | hard | groq-gpt-oss-20b | correct | 1356 | 0.000202 |
| reasoning-013 | reasoning | hard | groq-gpt-oss-120b | correct | 1494 | 0.000332 |
| structured_output-001 | structured_output | easy | groq-gpt-oss-20b | correct | 325 | 0.000029 |
| structured_output-001 | structured_output | easy | groq-gpt-oss-120b | correct | 462 | 0.000058 |
| structured_output-002 | structured_output | medium | groq-gpt-oss-20b | correct | 616 | 0.000033 |
| structured_output-002 | structured_output | medium | groq-gpt-oss-120b | correct | 465 | 0.000071 |
| structured_output-003 | structured_output | easy | groq-gpt-oss-20b | correct | 323 | 0.000037 |
| structured_output-003 | structured_output | easy | groq-gpt-oss-120b | correct | 538 | 0.000068 |
| structured_output-004 | structured_output | medium | groq-gpt-oss-20b | correct | 581 | 0.000040 |
| structured_output-004 | structured_output | medium | groq-gpt-oss-120b | correct | 567 | 0.000062 |
| structured_output-005 | structured_output | hard | groq-gpt-oss-20b | correct | 452 | 0.000035 |
| structured_output-005 | structured_output | hard | groq-gpt-oss-120b | correct | 592 | 0.000098 |
| structured_output-006 | structured_output | medium | groq-gpt-oss-20b | correct | 444 | 0.000043 |
| structured_output-006 | structured_output | medium | groq-gpt-oss-120b | correct | 453 | 0.000062 |
| structured_output-007 | structured_output | easy | groq-gpt-oss-20b | correct | 305 | 0.000030 |
| structured_output-007 | structured_output | easy | groq-gpt-oss-120b | correct | 521 | 0.000086 |
| structured_output-008 | structured_output | medium | groq-gpt-oss-20b | correct | 336 | 0.000055 |
| structured_output-008 | structured_output | medium | groq-gpt-oss-120b | correct | 535 | 0.000102 |
| structured_output-009 | structured_output | medium | groq-gpt-oss-20b | correct | 553 | 0.000067 |
| structured_output-009 | structured_output | medium | groq-gpt-oss-120b | correct | 451 | 0.000069 |
| structured_output-010 | structured_output | hard | groq-gpt-oss-20b | correct | 432 | 0.000062 |
| structured_output-010 | structured_output | hard | groq-gpt-oss-120b | correct | 860 | 0.000179 |
| structured_output-011 | structured_output | hard | groq-gpt-oss-20b | correct | 516 | 0.000068 |
| structured_output-011 | structured_output | hard | groq-gpt-oss-120b | correct | 935 | 0.000116 |
| structured_output-012 | structured_output | medium | groq-gpt-oss-20b | correct | 402 | 0.000035 |
| structured_output-012 | structured_output | medium | groq-gpt-oss-120b | correct | 517 | 0.000082 |
| structured_output-013 | structured_output | hard | groq-gpt-oss-20b | correct | 317 | 0.000050 |
| structured_output-013 | structured_output | hard | groq-gpt-oss-120b | correct | 725 | 0.000109 |
| summarization-001 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 454 | 0.000050 |
| summarization-001 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 464 | 0.000054 |
| summarization-002 | summarization | easy | groq-gpt-oss-20b | not_evaluated | 430 | 0.000036 |
| summarization-002 | summarization | easy | groq-gpt-oss-120b | not_evaluated | 1387 | 0.000042 |
| summarization-003 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 551 | 0.000043 |
| summarization-003 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 251 | 0.000047 |
| summarization-004 | summarization | hard | groq-gpt-oss-20b | not_evaluated | 492 | 0.000086 |
| summarization-004 | summarization | hard | groq-gpt-oss-120b | not_evaluated | 653 | 0.000093 |
| summarization-005 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 518 | 0.000056 |
| summarization-005 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 576 | 0.000049 |
| summarization-006 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 554 | 0.000042 |
| summarization-006 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 728 | 0.000088 |
| summarization-007 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 553 | 0.000057 |
| summarization-007 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 554 | 0.000049 |
| summarization-008 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 445 | 0.000033 |
| summarization-008 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 354 | 0.000048 |
| summarization-009 | summarization | hard | groq-gpt-oss-20b | not_evaluated | 386 | 0.000051 |
| summarization-009 | summarization | hard | groq-gpt-oss-120b | not_evaluated | 618 | 0.000081 |
| summarization-010 | summarization | hard | groq-gpt-oss-20b | not_evaluated | 634 | 0.000061 |
| summarization-010 | summarization | hard | groq-gpt-oss-120b | not_evaluated | 671 | 0.000056 |
| summarization-011 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 556 | 0.000042 |
| summarization-011 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 676 | 0.000099 |
| summarization-012 | summarization | hard | groq-gpt-oss-20b | not_evaluated | 650 | 0.000097 |
| summarization-012 | summarization | hard | groq-gpt-oss-120b | not_evaluated | 550 | 0.000084 |
| summarization-013 | summarization | medium | groq-gpt-oss-20b | not_evaluated | 448 | 0.000037 |
| summarization-013 | summarization | medium | groq-gpt-oss-120b | not_evaluated | 764 | 0.000081 |

**Actual billed cost (all 208 executions, both models): $0.00** - Groq free tier, no payment method on the account. The nominal_cost_usd column above is notional (registry per-1k pricing x real token counts), not what was actually charged.

## Quality/success rate by category (graded tasks only)

| category | n_graded | 20b correct | 20b rate | 120b correct | 120b rate |
|---|---|---|---|---|---|
| classification | 13 | 11 | 84.6% | 12 | 92.3% |
| coding | 13 | 13 | 100.0% | 13 | 100.0% |
| debugging | 5 | 5 | 100.0% | 5 | 100.0% |
| extraction | 13 | 10 | 76.9% | 10 | 76.9% |
| math | 13 | 11 | 84.6% | 10 | 76.9% |
| reasoning | 5 | 5 | 100.0% | 5 | 100.0% |
| structured_output | 13 | 13 | 100.0% | 13 | 100.0% |

## Quality/success rate by difficulty (graded tasks only)

| difficulty | n_graded | 20b correct | 20b rate | 120b correct | 120b rate |
|---|---|---|---|---|---|
| easy | 15 | 14 | 93.3% | 15 | 100.0% |
| medium | 33 | 30 | 90.9% | 30 | 90.9% |
| hard | 27 | 24 | 88.9% | 23 | 85.2% |

## Agreement breakdown (graded tasks only)

- both succeed: 65/75 (86.7%)
- only 20b succeeds: 3/75 (4.0%) - ['extraction-002', 'extraction-005', 'math-011']
- only 120b succeeds: 3/75 (4.0%) - ['classification-012', 'extraction-008', 'extraction-012']
- both fail: 4/75 (5.3%) - ['classification-010', 'extraction-004', 'math-005', 'math-013']

## Latency

- groq-gpt-oss-20b: avg 682ms across all 104 tasks
- groq-gpt-oss-120b: avg 1029ms across all 104 tasks
- 120b is 1.51x the latency of 20b on average

## Token usage

- groq-gpt-oss-20b: 11059 input + 31899 output = 42958 total tokens across all 104 tasks (avg 307 output tokens/task)
- groq-gpt-oss-120b: 11059 input + 29565 output = 40624 total tokens across all 104 tasks (avg 284 output tokens/task)
- 120b uses 0.93x the output tokens of 20b on average

## Cost

- groq-gpt-oss-20b: nominal total $0.010399 across all 104 tasks
- groq-gpt-oss-120b: nominal total $0.019398 across all 104 tasks
- 120b is 1.87x the nominal cost of 20b
- **actual billed cost for both: $0.00** (free tier, no payment method)

## How often does choosing 120b over 20b actually improve the result?

120b corrects a 20b failure on 3/75 graded tasks (4.0%), at 1.51x the latency and 1.87x the nominal cost, for a task set with no real cost difference today (both models are on Groq's free tier).

### The structural fact that decides this

- always-20b accuracy on the graded set: 65+3 = 68/75 = 90.7%
- always-120b accuracy on the graded set: 65+3 = 68/75 = 90.7%
- **these are equal** (3 vs 3) - neither model is a better unconditional default than the other on this task set.
- a perfect oracle router (always picks whichever of the two is correct, when either is) reaches 71/75 = 94.7% - a ceiling only 4.0% above either model alone, defined by just 6 tasks total.

## Evaluation gaps: tasks with no real ground truth yet

- **debugging**: 8 task(s) - ['debugging-001', 'debugging-002', 'debugging-003', 'debugging-004', 'debugging-005', 'debugging-006', 'debugging-007', 'debugging-008']
- **reasoning**: 8 task(s) - ['reasoning-001', 'reasoning-002', 'reasoning-003', 'reasoning-004', 'reasoning-005', 'reasoning-006', 'reasoning-009', 'reasoning-012']
- **summarization**: 13 task(s) - ['summarization-001', 'summarization-002', 'summarization-003', 'summarization-004', 'summarization-005', 'summarization-006', 'summarization-007', 'summarization-008', 'summarization-009', 'summarization-010', 'summarization-011', 'summarization-012', 'summarization-013']

