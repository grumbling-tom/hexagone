"use server";

import { redirect } from "next/navigation";
import type { CreateUploadRequest } from "@/__generated__/backend-client/backend.schemas";
import { createUpload } from "@/__generated__/backend-client/uploads";

// Creates the upload record and returns a presigned URL; the file bytes are
// PUT directly to object storage from the browser (that leg skips the backend).
export async function requestUpload(data: CreateUploadRequest) {
  return createUpload(data);
}

// Navigation handed to the upload feature so it stays routing-free: once the
// user has uploaded at least one file, send them to the map (which shows a
// processing state until the first file is parsed).
export async function finishOnboarding() {
  redirect("/map");
}
