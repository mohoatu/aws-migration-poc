# On-premise → AWS: a nightly batch job, migrated and proven

A small, complete migration: one legacy batch job moved from an on-premise
server to AWS object storage and managed compute, with **field-level evidence
that the numbers did not change**.

It runs end to end in about a minute, on a laptop, against a local AWS
emulator — and one environment variable away from real AWS.

---

## Why this exists

Most migration demos stop at "it runs in the cloud now". The part that actually
decides whether a programme cuts over is the part after that: **can anyone put
their name on a statement that the business outputs are unchanged?**

This PoC is built around that question. The migration itself is twenty lines of
plumbing. The evidence is the deliverable.

---

## The three runs

```bash
python run_cutover.py                      # exit 0  — GO
python run_cutover.py --drift rounding     # exit 0  — GO, 427 fields need a signature
python run_cutover.py --drift logic        # exit 1  — NO-GO, 110 records blocked
```

| Run | What changed in the cloud job | Verdict | Why |
|---|---|---|---|
| clean | nothing | **GO** | byte-for-byte identical to the on-premise output |
| `--drift rounding` | the last instalment rounds differently | **GO, with sign-off** | 427 amounts move by up to a cent. Real, but a business owner can accept it in writing |
| `--drift logic` | two branches of the status rule swapped | **NO-GO** | 110 records get a different status code. No signature can accept that |

The middle row is the one worth dwelling on. A tool that blocks on everything is
ignored within a week; a tool that blocks on nothing is decoration. The decision
that matters is **which differences a human must accept, and which no human
should be allowed to accept.**

The third row exists because *a gate that has never refused anything is not a
gate.* It is wired into the demo so the refusal can be shown, not promised.

---

## What happens in a run

```
[1] generate the night's input file
[2] run the legacy job on the on-premise server     Perl, local disk
[3] provision buckets, upload the same input        S3
[4] run the replatformed job                        S3 in → S3 out
[5] compare the two outputs field by field          GO / NO-GO + exit code
```

Step 5 writes `work/evidence.txt` — the artefact that goes in the cutover pack.

---

## Running it

Needs Python 3.10+ and a Perl. On Windows, Git for Windows ships a signed Perl
and the script finds it automatically.

```bash
python -m venv .venv
.venv/Scripts/python -m pip install "moto[server]" boto3

# start the local AWS emulator
.venv/Scripts/python -m moto.server -p 5000

# in another shell
.venv/Scripts/python run_cutover.py
```

**Against real AWS:** unset `AWS_ENDPOINT_URL` and supply credentials. No code
changes — see `aws/worker.py`, where that is a single line.

---

## Layout

```
run_cutover.py        the parallel run and the gate
aws/provision.py      creates the buckets, idempotent
aws/worker.py         the replatformed job: S3 in, S3 out
docs/                 the programme artefacts — see below
work/                 generated; evidence.txt lands here
```

The comparator lives in a separate repo (`migration-verify`) and is reused
as-is.

---

## The programme artefacts

The code is the small half. For a migration of any size these are the half that
decides whether it lands:

| | |
|---|---|
| [`docs/01-current-state.md`](docs/01-current-state.md) | what the job is, what it touches, what breaks if it is wrong |
| [`docs/02-disposition-7rs.md`](docs/02-disposition-7rs.md) | why replatform, and why not rehost or refactor |
| [`docs/03-target-architecture.md`](docs/03-target-architecture.md) | the AWS design, and what this PoC deliberately leaves out |
| [`docs/04-cutover-runbook.md`](docs/04-cutover-runbook.md) | the cutover, step by step, with rollback triggers |
| [`docs/05-success-criteria.md`](docs/05-success-criteria.md) | what "done" means, agreed before testing starts |
| [`docs/06-risk-register.md`](docs/06-risk-register.md) | what could go wrong, who owns it |

---

## What this PoC is not

Stated plainly, because a PoC that pretends to be production is worse than no
PoC:

- **No IAM, no encryption, no VPC, no least-privilege.** A real design starts
  there. `docs/03` lists what is missing and what it would cost to add.
- **Runs against an emulator by default.** The AWS API calls are real; the
  account is not. Nothing here proves anything about quotas, latency or billing.
- **One job, 1,200 records.** A real programme has dozens of jobs, interdependencies
  and a wave plan. `docs/04` describes how this scales; the PoC does not.
- **The comparator has limits of its own**, documented in its own repo: no
  packed-decimal or EBCDIC, no test above a few million rows, and a date-format
  ambiguity that must be declared rather than guessed.
