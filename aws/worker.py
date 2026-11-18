#!/usr/bin/env python3
"""PREMCALC on AWS — the replatformed nightly batch job.

Reads the input object from S3, computes, writes the report object back to S3.
On real AWS this runs as an ECS Fargate task (see docs/03-target-architecture.md);
locally it runs against a moto endpoint. The code does not know the difference —
that is the point of `AWS_ENDPOINT_URL`.

This is a faithful port of `onprem/premcalc.pl`. Faithful is the requirement, not
an aspiration: the whole programme is judged on whether the migrated job produces
the same numbers, and "we improved the rounding while we were in there" is how a
migration turns into an incident.

Two places where fidelity needed care:

  - Perl and Python both use IEEE doubles and both delegate `%.2f` to the C
    library, so the half-to-even rounding behaviour matches. A port to Java
    BigDecimal would NOT match - see migration-verify/legacy-demo for what that
    costs.
  - The report shows the LAST instalment when there is more than one, which is
    what the legacy program does. The specification never said so. Porting from
    the spec instead of from the code produces 354 different records; that
    difference is the subject of the evidence pack.

    python worker.py --in-bucket X --in-key Y --out-bucket Z --out-key W
"""

import argparse
import io
import os

import boto3


def s3_client():
    """One client for both worlds.

    AWS_ENDPOINT_URL set   -> local emulator (moto)
    AWS_ENDPOINT_URL unset -> real AWS, resolved the normal way

    Keeping this a single line of difference is deliberate: a PoC that only runs
    against an emulator proves nothing about the migration. This one is one
    environment variable away from the real thing.
    """
    return boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)


def process(lines):
    out = []
    count = 0
    sum_due = 0.0

    for line in lines:
        line = line.rstrip("\n").rstrip("\r")
        if not line.strip():
            continue

        # Fixed-width layout, same offsets as the legacy unpack template.
        pid = line[0:10].strip()
        principal = int(line[18:27]) / 100
        rate_bp = int(line[27:32])
        term_days = int(line[32:36])
        instalments = int(line[36:38])
        tier = line[38:39]

        accrual_days = 365 if term_days > 365 else term_days
        daily_rate = (rate_bp / 10000) / 365
        interest = principal * daily_rate * accrual_days
        total_due = principal + interest

        instal = float("%.2f" % (total_due / instalments))
        running = instal * (instalments - 1)
        last = float("%.2f" % (total_due - running))
        instal_shown = last if instalments > 1 else instal

        if tier == "3" and principal > 40000:
            status = "PD"
        elif accrual_days == 365:
            status = "MX"
        elif instalments == 1:
            status = "LS"
        else:
            status = "AP"

        sum_due += total_due
        count += 1

        out.append("%-10s%04d%10.2f%10.2f%10.2f%-2s%-14s"
                   % (pid, accrual_days, instal_shown, interest, total_due,
                      status, ""))

    out.append("%-10s%06d%12.2f%-52s" % ("TRAILER", count, sum_due, ""))
    return "\n".join(out) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in-bucket", required=True)
    ap.add_argument("--in-key", required=True)
    ap.add_argument("--out-bucket", required=True)
    ap.add_argument("--out-key", required=True)
    args = ap.parse_args()

    s3 = s3_client()

    body = s3.get_object(Bucket=args.in_bucket, Key=args.in_key)["Body"].read()
    text = body.decode("ascii")
    report = process(io.StringIO(text))

    s3.put_object(Bucket=args.out_bucket, Key=args.out_key,
                  Body=report.encode("ascii"))

    n = report.count("\n") - 1
    print(f"wrote s3://{args.out_bucket}/{args.out_key}  ({n} records + trailer)")


if __name__ == "__main__":
    main()
