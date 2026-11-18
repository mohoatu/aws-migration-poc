#!/usr/bin/env python3
"""Parallel run and cutover gate, end to end.

    python run_cutover.py            # the real demo
    python run_cutover.py --drift    # same, with one rule changed in the cloud job

What it does:

  1. Runs the legacy job on local disk          (the "on-premise server")
  2. Uploads the same input to S3               (landing bucket)
  3. Runs the replatformed worker against S3    (ECS Fargate on real AWS)
  4. Downloads the cloud output
  5. Compares the two field by field and returns a GO / NO-GO exit code

Step 5 is the part that matters. Anybody can move a job to the cloud; the
programme is not finished until somebody can sign a piece of paper saying the
numbers did not change. That signature needs evidence, and this produces it.

`--drift` exists because a gate that has never refused anything is not a gate.
It changes exactly one rule in the cloud job - the rounding mode on the
instalment - and the run must come back NO-GO. If it does not, the gate is
decoration.

Needs the emulator running (see README), or real AWS credentials with
AWS_ENDPOINT_URL unset.
"""

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent
ONPREM = ROOT / "onprem"
WORK = ROOT / "work"
VERIFY = ROOT.parent / "migration-verify"

LANDING = "premcalc-landing"
RESULTS = "premcalc-results"
IN_KEY = "in/policies.dat"
OUT_KEY = "out/report.txt"

PY = sys.executable


def find_perl():
    """Locate a Perl that is allowed to run on this machine.

    The legacy job is Perl on purpose - that is the point of a legacy job - but
    Windows has no Perl, and the MSYS2 one is blocked here by Smart App Control
    (unsigned binaries). Git for Windows ships a signed Perl, so that is the one
    that actually runs. Worth knowing before promising a client a demo on their
    locked-down laptop.
    """
    found = shutil.which("perl")
    if found:
        return found
    for c in (r"C:\Program Files\Git\usr\bin\perl.exe",
              r"C:\Program Files (x86)\Git\usr\bin\perl.exe",
              "/usr/bin/perl"):
        if pathlib.Path(c).exists():
            return c
    sys.exit("No Perl found. Install Git for Windows (it ships one), "
             "or run this on Linux.")


def sh(cmd, cwd=None, env=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        print(p.stdout)
        print(p.stderr, file=sys.stderr)
        sys.exit(f"FAILED: {' '.join(str(c) for c in cmd)}")
    return p


def step(n, text):
    print(f"\n[{n}] {text}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drift", choices=["rounding", "logic"],
                    help="change one rule in the cloud job and see how it is "
                         "classified: `rounding` needs a signature, `logic` "
                         "stops the release")
    args = ap.parse_args()

    WORK.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.setdefault("AWS_ENDPOINT_URL", "http://127.0.0.1:5000")
    env.setdefault("AWS_ACCESS_KEY_ID", "test")
    env.setdefault("AWS_SECRET_ACCESS_KEY", "test")
    env.setdefault("AWS_DEFAULT_REGION", "ap-southeast-1")
    # Children print Vietnamese; the Windows console default is cp1252 and would
    # kill them mid-run. Same failure that took a day to diagnose on 12/11.
    env["PYTHONIOENCODING"] = "utf-8"

    where = env["AWS_ENDPOINT_URL"] or "real AWS"
    print(f"Target: {where}")

    # ---- 1. input -----------------------------------------------------------
    step(1, "Generating the night's input file")
    sh([PY, str(VERIFY / "legacy-demo" / "gen_policies.py")], cwd=WORK)

    # ---- 2. the legacy job, on local disk -----------------------------------
    step(2, "Running the legacy job on the on-premise server (Perl, local disk)")
    sh([find_perl(), str(VERIFY / "legacy-demo" / "legacy" / "premcalc.pl"),
        "policies.dat", "onprem_out.txt"], cwd=WORK)

    # ---- 3. provision + upload ----------------------------------------------
    step(3, "Provisioning buckets and uploading the same input")
    sh([PY, str(ROOT / "aws" / "provision.py")], env=env)

    import boto3
    s3 = boto3.client("s3", endpoint_url=env["AWS_ENDPOINT_URL"] or None,
                      aws_access_key_id=env["AWS_ACCESS_KEY_ID"],
                      aws_secret_access_key=env["AWS_SECRET_ACCESS_KEY"],
                      region_name=env["AWS_DEFAULT_REGION"])
    s3.upload_file(str(WORK / "policies.dat"), LANDING, IN_KEY)

    # ---- 4. the replatformed job --------------------------------------------
    step(4, "Running the replatformed job (S3 in, S3 out)")
    worker = ROOT / "aws" / "worker.py"
    if args.drift:
        # One rule changed, nothing else — what a careless port actually looks
        # like. Two flavours, because they are not the same kind of problem and
        # the whole value of the gate is telling them apart:
        #
        #   rounding — somebody "improved" the rounding on the way past. The
        #              money moves by a cent. Real, but a signature can accept it.
        #   logic    — somebody reordered an if-chain. Records that match two
        #              rules now get the other answer. Nothing can accept that
        #              except a fix.
        drifted = WORK / "worker_drifted.py"
        src = worker.read_text(encoding="utf-8")
        if args.drift == "rounding":
            src = src.replace('last = float("%.2f" % (total_due - running))',
                              'last = round(total_due - running + 0.005, 2)  # DRIFT')
        else:
            src = src.replace(
                '        if tier == "3" and principal > 40000:\n'
                '            status = "PD"\n'
                '        elif accrual_days == 365:\n'
                '            status = "MX"',
                '        if accrual_days == 365:          # DRIFT: branches swapped\n'
                '            status = "MX"\n'
                '        elif tier == "3" and principal > 40000:\n'
                '            status = "PD"')
        if "DRIFT" not in src:
            sys.exit("drift patch did not apply - worker.py changed shape")
        drifted.write_text(src, encoding="utf-8")
        worker = drifted
        print(f"    (running the DRIFTED build on purpose: {args.drift})")

    sh([PY, str(worker), "--in-bucket", LANDING, "--in-key", IN_KEY,
        "--out-bucket", RESULTS, "--out-key", OUT_KEY], env=env)

    s3.download_file(RESULTS, OUT_KEY, str(WORK / "cloud_out.txt"))

    # ---- 5. the gate ---------------------------------------------------------
    step(5, "Comparing on-premise output against cloud output, field by field")
    shutil.copy(VERIFY / "legacy-demo" / "schema.json", WORK / "schema.json")
    p = sh([PY, str(VERIFY / "spike" / "verify.py"),
            "onprem_out.txt", "cloud_out.txt", "schema.json", "--lang=en"],
           cwd=WORK, env=env, check=False)
    print(p.stdout)

    (WORK / "evidence.txt").write_text(p.stdout, encoding="utf-8")

    print("=" * 70)
    if p.returncode == 0:
        print("GO — the cloud job reproduces the on-premise output. "
              "Evidence: work/evidence.txt")
    else:
        print("NO-GO — differences need a decision before cutover. "
              "Evidence: work/evidence.txt")
    print("=" * 70)
    return p.returncode


if __name__ == "__main__":
    sys.exit(main())
