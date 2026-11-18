# Cutover runbook — PREMCALC

Owner: migration lead · Approver: finance domain owner · Window: 01:00–03:00

Written before the parallel run, not after. A runbook drafted the week of
cutover is a wish list.

---

## Entry criteria — all must hold, checked the day before

| # | Criterion | Evidence | Owner |
|---|---|---|---|
| 1 | Ten consecutive parallel runs with **zero blocking differences** | `work/evidence.txt` per run, archived | migration lead |
| 2 | All rounding differences accepted **in writing** | signed tolerance sheet (`docs/05`) | finance domain owner |
| 3 | Legacy job can still run | last successful on-premise run ≤ 24 h old | platform team |
| 4 | Downstream consumers notified of the new object location | email, acknowledged | migration lead |
| 5 | Rollback rehearsed at least once | rehearsal notes | platform team |

If criterion 1 or 2 fails, the cutover does not happen. Those are not
negotiable on the night — that is the whole reason they are written down now,
when nobody is tired and the room is calm.

---

## Sequence

| T | Step | Expected | If it fails |
|---|---|---|---|
| −30m | Freeze input: stop the upstream feed | no new files landing | abort, reschedule |
| −20m | Final on-premise run on the frozen input | report produced, archived as the baseline | abort |
| −10m | Upload the same input to the landing bucket | object present, size matches | retry once, then abort |
| 0 | Run the cloud job | task exits 0 | → rollback |
| +10m | **Run the gate**: compare cloud output to the baseline | **exit 0** | → rollback |
| +15m | Point downstream consumers at the new location | consumers read the new object | → rollback |
| +20m | Disable the legacy scheduler entry (**do not delete**) | cron disabled | — |
| +30m | Unfreeze the upstream feed | normal operation | — |

---

## Rollback

Three steps, because the legacy job was never removed:

1. Re-enable the legacy scheduler entry.
2. Point downstream consumers back at the on-premise path.
3. Leave the cloud output in place for investigation — do not delete it.

**Rollback triggers — any one of these, no debate at 2 a.m.:**

- the gate returns non-zero
- the cloud job has not finished by +15m
- any downstream consumer cannot read the new object
- anyone in the room is unsure

The last one is deliberate and is the most useful line in this document. The
cost of rolling back is one night. The cost of shipping wrong instalment
figures to customers is not measured in nights.

---

## After cutover

- Keep the legacy job **runnable but disabled** for one full billing cycle.
- Keep running the gate nightly against the final baseline for two weeks: it
  catches drift from data the parallel run never saw, which is where month-end
  surprises live.
- Decommission only after a clean month-end.

---

## Scaling this to the real programme

This runbook covers one job. For the full estate:

- group jobs into **waves by downstream dependency**, not by team convenience
- each wave gets its own entry criteria and its own gate run
- the first wave should be the job with the **fewest consumers**, not the
  easiest to migrate — the point of wave one is to test the process, and a job
  with three consumers tests it properly while staying recoverable
