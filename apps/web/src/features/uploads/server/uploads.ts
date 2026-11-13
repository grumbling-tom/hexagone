"use server";

import type {
  CreateUploadRequest,
  ListUploadsParams,
} from "@/__generated__/backend-client/backend.schemas";
import { createUploadProcessingJob } from "@/__generated__/backend-client/upload-processing-jobs";
import {
  createUpload,
  listUploads,
} from "@/__generated__/backend-client/uploads";

export async function fetchUploads(params: ListUploadsParams) {
  return listUploads(params);
}

export async function requestUpload(data: CreateUploadRequest) {
  return createUpload(data);
}

// Called once the browser has finished PUTting the file to storage: the
// backend turns it into hexagons and returns the upload's final status.
export async function processUpload(uploadUid: string) {
  return createUploadProcessingJob({ upload_uid: uploadUid });
}
