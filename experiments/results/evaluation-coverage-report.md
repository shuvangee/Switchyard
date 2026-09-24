# Evaluation coverage report

- total benchmark tasks: 104
- automatically graded (real ground truth, both models): 84
- manual-only (evaluation_type=manual, no automated grader applied): 19
- ungraded (automated evaluation_type, but not currently scored - a gap): 1
- percentage with automated quality labels: 80.8%

## Coverage by category

| category | total | automatically graded | manual-only | ungraded | automated % |
|---|---|---|---|---|---|
| classification | 13 | 13 | 0 | 0 | 100.0% |
| coding | 13 | 13 | 0 | 0 | 100.0% |
| debugging | 13 | 5 | 8 | 0 | 38.5% |
| extraction | 13 | 13 | 0 | 0 | 100.0% |
| math | 13 | 13 | 0 | 0 | 100.0% |
| reasoning | 13 | 8 | 4 | 1 | 61.5% |
| structured_output | 13 | 13 | 0 | 0 | 100.0% |
| summarization | 13 | 6 | 7 | 0 | 46.2% |

## Ungraded tasks (genuine gap - investigate before trusting coverage numbers)

- **reasoning**: ['reasoning-005']

## Manual-only tasks (deliberate, not a gap)

- **debugging**: ['debugging-001', 'debugging-002', 'debugging-003', 'debugging-004', 'debugging-005', 'debugging-006', 'debugging-007', 'debugging-008']
- **reasoning**: ['reasoning-004', 'reasoning-006', 'reasoning-009', 'reasoning-012']
- **summarization**: ['summarization-001', 'summarization-002', 'summarization-003', 'summarization-004', 'summarization-009', 'summarization-011', 'summarization-012']

