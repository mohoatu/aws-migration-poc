#!/usr/bin/env python3
"""Create the two buckets the job needs. Idempotent.

Deliberately plain boto3 rather than Terraform or CDK, for one reason worth
stating in an interview: on this machine Smart App Control blocks unsigned
binaries, and `terraform.exe` is an unsigned download. Choosing tooling that
survives the customer's security posture is part of the job, not a compromise.

On a real engagement this would be CloudFormation or CDK under a pipeline, with
the buckets versioned, encrypted and lifecycle-managed - see
docs/03-target-architecture.md for what is missing here and why.
"""

import os
import sys

import boto3
from botocore.exceptions import ClientError

LANDING = "premcalc-landing"
RESULTS = "premcalc-results"


def ensure(s3, name, region):
    try:
        kw = {"Bucket": name}
        if region != "us-east-1":
            kw["CreateBucketConfiguration"] = {"LocationConstraint": region}
        s3.create_bucket(**kw)
        print(f"  created  {name}")
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("BucketAlreadyOwnedByYou", "BucketAlreadyExists"):
            print(f"  exists   {name}")
        else:
            raise


def main():
    region = os.environ.get("AWS_DEFAULT_REGION", "ap-southeast-1")
    s3 = boto3.client("s3", endpoint_url=os.environ.get("AWS_ENDPOINT_URL") or None)
    for b in (LANDING, RESULTS):
        ensure(s3, b, region)
    return 0


if __name__ == "__main__":
    sys.exit(main())
