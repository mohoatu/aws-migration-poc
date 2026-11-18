# Disposition: why replatform

The AWS 7Rs, applied to PREMCALC. The point of writing this down is not the
answer — it is that the answer was argued before anyone wrote code, and the
rejected options are recorded so nobody re-litigates them in month four.

| Option | Verdict | Reasoning |
|---|---|---|
| **Retire** | No | The job produces the instalment schedule finance bills from. Nothing else produces it. |
| **Retain** | No | The server it runs on leaves support next year; that is what started this. |
| **Rehost** (lift and shift to EC2) | No | Moves the problem. We would own patching, backups and a 3 a.m. cron on a box in a different building. Cheapest to do, most expensive to keep. |
| **Replatform** | **Yes** | Same business logic, managed infrastructure underneath. Object storage instead of a filesystem, a scheduled container instead of cron. The code barely changes, which is exactly what makes it verifiable. |
| **Repurchase** | No | No off-the-shelf product computes this firm's instalment rules. |
| **Refactor** | Not now | Rewriting the logic while moving it means two sources of error at once, and no way to tell which one produced a difference. Refactor afterwards, against a baseline that is known good. |
| **Relocate** | N/A | Not a VMware estate. |

---

## The decision that actually matters

Not replatform-versus-rehost. It is **refactor now or refactor later**, and the
answer is later.

A migration that changes the logic at the same time as the platform cannot be
verified. When a number comes out different, nobody can say whether the cloud
move did it or the rewrite did it, and the investigation costs more than the
rewrite saved. Move it unchanged, prove it unchanged, then improve it with a
baseline you trust.

This is also what makes the evidence in `run_cutover.py` meaningful. Because the
logic was held still, **any** difference is a defect — so the comparison has
teeth. If we had refactored at the same time, differences would be expected, and
"expected differences" is where migrations go to die.

---

## Compute: why not Lambda

The obvious replatform target for a batch job is Lambda, and it is the wrong one
here.

- Lambda stops at **15 minutes**. This job is small today; the same programme
  covers jobs that run forty minutes at month-end. Designing one pattern for
  small jobs and a second for large ones doubles the work and the ways to fail.
- Batch jobs want **retry and failure semantics** at task level, not per
  invocation.

**ECS Fargate tasks on an EventBridge schedule**, with AWS Batch if dependency
chains appear. Same container runs locally, in CI and in production.

Choosing Lambda because it demos nicely would be the kind of decision that looks
clever in week one and is unpicked in month six.

---

## What this costs if we are wrong

Replatform is reversible for about a sprint: the legacy job still exists, the
server is still there during parallel run, and cutover is a scheduler change.
That reversibility is bought by **not** refactoring, and it is the reason the
rollback section of the runbook is three lines instead of three pages.
