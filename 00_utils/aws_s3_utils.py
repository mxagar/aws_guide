"""
This module contains interaction examples with AWS S3 using boto3.

For authentication, we have several options:

1. Save temporary credentials as environment variables, for instance in `.env` (used here).
2. Save temporary credentials in `~/.aws/credentials`.

Example `~/.aws/credentials` (not used here):

```
[myprofile]
aws_access_key_id = your_AWS_ACCESS_KEY_ID
aws_secret_access_key = your_AWS_SECRET_ACCESS_KEY
aws_session_token = your_AWS_SESSION_TOKEN
aws_default_region = your_AWS_DEFAULT_REGION
```

In our code, we can authenticate as follows, depending on the case:

    # 1. Enviornment variables (used here):
    # ... 
    load_dotenv()
    s3_client = boto3.client('s3')

    # 2. ~/.aws/credentials (not used here):
    # ...
    session = boto3.Session(profile_name='myprofile')
    s3_client = session.client('s3')

Author: Mikel Sagardia.
Date: 2024-11-15.
"""
import os
from typing import Optional
from dotenv import load_dotenv
from tqdm import tqdm
from pathlib import Path

import boto3
import botocore
import pandas as pd


def create_s3_client() -> boto3.client:
    """Create an S3 client."""
    # Get credentials from .env file
    load_dotenv()
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", default=None)
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", default=None)
    AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN", default=None)
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", default=None)
    if AWS_ACCESS_KEY_ID is None \
        or AWS_SECRET_ACCESS_KEY is None \
        or AWS_SESSION_TOKEN is None \
        or AWS_DEFAULT_REGION is None:
        error_message = "Missing AWS credentials in .env file"
        raise ValueError(error_message)

    # Create S3 client
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        aws_session_token=AWS_SESSION_TOKEN,
        region_name=AWS_DEFAULT_REGION
    )

    return s3_client


def list_buckets(s3_client: Optional[boto3.client] = None) -> None:
    if s3_client is None:
        s3_client = create_s3_client()
    buckets = s3_client.list_buckets()
    print("Available Buckets:")
    for bucket in buckets["Buckets"]:
        print(f"  - {bucket['Name']}")


def create_s3_bucket(bucket_name: str, s3_client: Optional[boto3.client] = None) -> None:
    if s3_client is None:
        s3_client = create_s3_client()
    region = s3_client.meta.region_name

    try:
        _ = s3_client.create_bucket(
            Bucket=bucket_name,
            CreateBucketConfiguration={
                "LocationConstraint": region
            }
        )
        print(f"Bucket {bucket_name} created successfully in region {region}.")
    except botocore.exceptions.ClientError as e:
        print(f"Error: {e.response['Error']['Message']}")


def delete_s3_bucket(bucket_name: str, s3_client: Optional[boto3.client] = None) -> None:
    if s3_client is None:
        s3_client = create_s3_client()

    try:
        _ = s3_client.delete_bucket(Bucket=bucket_name)
        print(f"Bucket {bucket_name} deleted successfully.")
    except botocore.exceptions.ClientError as e:
        print(f"Error: {e.response['Error']['Message']}")


def get_file_entries_in_bucket(bucket_name: str,
                               s3_client: Optional[boto3.client] = None) -> list:
    if s3_client is None:
        s3_client = create_s3_client()
    file_entries = []

    try:
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in tqdm(paginator.paginate(Bucket=bucket_name),
                         desc="Retrieving files from bucket", unit="page"):
            if "Contents" in page:
                file_entries.extend(page["Contents"])
        print(f"Total files found: {len(file_entries)}")
    except Exception as e:
        print(f"Error: {e}")

    return file_entries


def print_filenames_in_bucket(bucket_name: str,
                             s3_client: Optional[boto3.client] = None) -> None:
    file_entries = get_file_entries_in_bucket(bucket_name, s3_client=s3_client)
    if len(file_entries) > 0:
        for file in file_entries:
            print(file["Key"])


def organize_file_entries_into_dataframe(file_entries: list) -> pd.DataFrame:
    data = []
    for entry in file_entries:
        token, filename = entry['Key'].split('/', 1)
        modified = entry['LastModified']
        size = entry['Size']
        data.append({'token': token, 'filename': filename, 'las_modified': modified, 'size': size})

    df = pd.DataFrame(data)

    return df


def download_file_from_s3(bucket_name: str,
                          object_name: str,
                          file_name: Optional[str] = None,
                          s3_client: Optional[boto3.client] = None) -> None:
    if s3_client is None:
        s3_client = create_s3_client()
    if file_name is None:
        file_name = object_name

    # Ensure all directories in the file path are created
    if "/" in file_name:
        Path(file_name).parent.mkdir(parents=True, exist_ok=True)

    try:
        s3_client.download_file(bucket_name, object_name, file_name)
    except Exception as e:
        print(f"Error downloading file: {e}")


def upload_file_to_s3(bucket_name: str,
                      file_name: str,
                      object_name: Optional[str] = None,
                      s3_client: Optional[boto3.client] = None) -> None:
    if s3_client is None:
        s3_client = create_s3_client()
    if object_name is None:
        object_name = file_name

    try:
        s3_client.upload_file(file_name, bucket_name, object_name)
    except Exception as e:
        print(f"Error uploading file: {e}")


def delete_file_from_s3(bucket_name: str,
                        object_name: str,
                        s3_client: Optional[boto3.client] = None) -> None:
    if s3_client is None:
        s3_client = create_s3_client()

    try:
        s3_client.delete_object(Bucket=bucket_name, Key=object_name)
    except Exception as e:
        print(f"Error deleting file: {e}")
