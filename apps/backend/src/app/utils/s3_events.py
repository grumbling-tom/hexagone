"""Pydantic models for S3 ObjectCreated event notifications."""

from pydantic import BaseModel


class S3BucketInfo(BaseModel):
    name: str


class S3ObjectInfo(BaseModel):
    key: str


class S3Info(BaseModel):
    bucket: S3BucketInfo
    object: S3ObjectInfo


class S3EventRecord(BaseModel):
    s3: S3Info


class S3Event(BaseModel):
    Records: list[S3EventRecord]
