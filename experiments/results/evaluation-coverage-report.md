# Evaluation coverage report

- total benchmark tasks: 104
- automatically graded (real ground truth, both models): 92
- manual-only (evaluation_type=manual, no automated grader applied): 12
- ungraded (automated evaluation_type, but not currently scored - a gap): 0
- percentage with automated quality labels: 88.5%

## Coverage by category

| category | total | automatically graded | manual-only | ungraded | automated % |
|---|---|---|---|---|---|
| classification | 13 | 13 | 0 | 0 | 100.0% |
| coding | 13 | 13 | 0 | 0 | 100.0% |
| debugging | 13 | 12 | 1 | 0 | 92.3% |
| extraction | 13 | 13 | 0 | 0 | 100.0% |
| math | 13 | 13 | 0 | 0 | 100.0% |
| reasoning | 13 | 9 | 4 | 0 | 69.2% |
| structured_output | 13 | 13 | 0 | 0 | 100.0% |
| summarization | 13 | 6 | 7 | 0 | 46.2% |

## Ungraded tasks

None - every automated-evaluation_type task currently has real ground truth for both models.

## Manual-only tasks (deliberate, not a gap)

- **debugging**: ['debugging-007']
- **reasoning**: ['reasoning-004', 'reasoning-006', 'reasoning-009', 'reasoning-012']
- **summarization**: ['summarization-001', 'summarization-002', 'summarization-003', 'summarization-004', 'summarization-009', 'summarization-011', 'summarization-012']

