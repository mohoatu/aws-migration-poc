# Current state — PREMCALC

## What it is

A nightly batch job that reads the day's policy file, computes accrued interest
and the instalment schedule, and writes a fixed-width report. Finance bills from
that report.

| | |
|---|---|
| Language | Perl 5, one file, written around 2004 |
| Trigger | `cron`, 02:15 daily, on a single on-premise server |
| Input | `policies.dat` — fixed-width, ~1,200 records/night, dropped by an upstream feed |
| Output | fixed-width report + a control-total trailer line |
| Consumers | finance billing run, a reporting extract, an archive copy |
| Tests | none |
| Documentation | none that matches the code |
| Runtime | under a minute; ~40 minutes at month-end on the largest sibling job |

## Why it is being moved

The server leaves vendor support next year. That is the whole trigger — nobody
is asking for new features, and nobody wants the logic changed.

## What makes it risky

**Nobody fully understands it.** The author left. The rules that exist in the
code are not all written down anywhere, and the places where the code and the
specification disagree are unknown until something compares them.

**It is silently wrong-able.** A failure that crashes is cheap: the run is
retried. A failure that completes and produces slightly different money is the
expensive one, because it reaches customers before anyone notices.

**The control total is the only existing check**, and it only catches gross
errors. A few hundred records changing by a cent each will pass it.

## Dependencies

- upstream feed writes `policies.dat` to a shared filesystem path
- downstream billing reads the report from a second path on the same filesystem
- both paths are hard-coded in the script

Those two hard-coded paths are the actual migration work. Everything else is
arithmetic that does not care where it runs.

## Service expectations

| | |
|---|---|
| Must complete by | 05:00, before the billing run starts |
| Acceptable failure | a crash, caught and retried |
| Unacceptable failure | completing with different numbers |

That last row is the one the whole programme is designed around.
