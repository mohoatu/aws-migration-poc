# Target architecture

```
  upstream feed                                     downstream billing
        |                                                   ^
        v                                                   |
  s3://premcalc-landing/in/      EventBridge          s3://premcalc-results/out/
        |                        (schedule)                 ^
        |                             |                     |
        +----------------->  ECS Fargate task  -------------+
                             (the job, in a container)
                                      |
                                      v
                              CloudWatch Logs + alarm
```

| Concern | On-premise today | On AWS |
|---|---|---|
| Input / output | shared filesystem paths | S3 objects, versioned |
| Schedule | `cron` on one box | EventBridge Scheduler |
| Compute | that same box | ECS Fargate task |
| Failure visibility | nobody looks | CloudWatch alarm on task failure and on no-run |
| Capacity | fixed | per-task sizing |

The job itself changes in one place: file paths become object keys. That is the
definition of replatform, and it is deliberate — see `02-disposition-7rs.md`.

## Why Fargate and not Lambda

Lambda caps at 15 minutes; the month-end sibling job runs forty. One pattern for
all batch jobs beats two patterns and a rule about which to use.

## What this PoC leaves out, and what it would cost

Stated so nobody mistakes the PoC for a design:

| Missing | Why it matters | Rough effort |
|---|---|---|
| IAM least-privilege roles | the PoC uses blanket credentials; production needs a task role scoped to two prefixes | 1 day |
| Encryption (SSE-KMS) and bucket policies | finance data at rest; likely an audit finding without it | 1 day |
| VPC endpoints for S3 | keeps traffic off the public internet; usually a security requirement | 1 day |
| Versioning + lifecycle + retention | the control total is only auditable if yesterday's output still exists | 0.5 day |
| Alarm on *absence* of a run | a job that never starts is the failure nobody notices | 0.5 day |
| Infrastructure as code under a pipeline | the PoC provisions with boto3; production needs CloudFormation or CDK, reviewed | 2 days |
| Dead-letter / retry policy | what happens when the input is malformed | 1 day |

About two weeks of engineering, none of it interesting, all of it required.
A plan that omits this line is a plan that slips.

## Well-Architected, briefly

- **Operational excellence** — the nightly gate is the operational check; alarms cover task failure and non-start.
- **Security** — the gaps above are the plan, not an oversight.
- **Reliability** — the legacy job stays runnable through parallel run and one billing cycle after.
- **Performance** — task sizing per job; no shared box to contend on.
- **Cost** — Fargate per-second billing for a job that runs minutes a day, versus a server running always.
- **Sustainability** — same argument as cost.
