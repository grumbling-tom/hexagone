"use server";

import { redirect } from "next/navigation";
import { deleteCurrentSession } from "@/__generated__/backend-client/user-sessions";

export async function logout(): Promise<void> {
  await deleteCurrentSession();
  redirect("/login");
}
