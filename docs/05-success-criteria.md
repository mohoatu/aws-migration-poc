# Success criteria

Agreed **before** the parallel run starts. Criteria written after seeing results
are not criteria.

## Go-live gates

| # | Criterion | Measured by | Signed by |
|---|---|---|---|
| 1 | Zero blocking differences across 10 consecutive nightly runs | `run_cutover.py` exit code | migration lead |
| 2 | Every non-blocking difference reviewed and accepted in writing | tolerance sheet below | finance domain owner |
| 3 | Control total matches to the cent, or the variance is accepted | trailer comparison in the evidence file | finance domain owner |
| 4 | Cloud job completes before 05:00 on the largest input seen | task duration in CloudWatch | platform owner |
| 5 | Rollback rehearsed end to end | rehearsal notes | platform owner |

## Difference classes and who decides

The comparator sorts every difference into a class. Who may accept what is
decided here, not in the moment:

| Class | Meaning | Who may accept it |
|---|---|---|
| run-variable | timestamps, batch sequence | nobody needs to — ignored by declaration |
| formatting | same value, written differently | migration lead |
| rounding | within one representable unit of the field | **finance domain owner, in writing** |
| business | logic changed | **nobody** — it is fixed or the cutover waits |
| missing / extra | records vanished or appeared | **nobody** — same |

Engineering does not set the money tolerance. That is a business decision and it
is recorded with a name and a date.

## Tolerance sheet

| Field | Type | Tolerance | Approved by | Date |
|---|---|---|---|---|
| `instalment` | decimal(2) | ±0.01 | [FILL] | [FILL] |
| `interest` | decimal(2) | ±0.01 | [FILL] | [FILL] |
| `total_due` | decimal(2) | ±0.01 | [FILL] | [FILL] |
| `accrual_days` | integer | **none** | — | — |
| `status` | string | **none** | — | — |

Integers and status codes get no tolerance, ever. They are causes, not outputs:
money differences can hide inside a rounding allowance, but a day count off by
one or a status code that changed cannot be anything other than a logic
difference.

## Explicitly not success criteria

- "The job runs in AWS." It ran in AWS on day one; that was never the hard part.
- "No differences at all." Rounding differences are expected and acceptable —
  demanding zero would stall the programme on a cent.
- "The team is confident." Confidence is not evidence.
