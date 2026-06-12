"use server";

import type {
  CreateUploadRequest,
  ListUploadsParams,
} from "@/__generated__/backend-client/backend.schemas";
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
