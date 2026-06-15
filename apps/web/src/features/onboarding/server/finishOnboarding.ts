"use server";

import { redirect } from "next/navigation";

// Navigation handed to the upload feature so its components stay routing-free:
// once the user has uploaded at least one file, send them to the map (which
// shows a processing state until the first file is parsed). Server Actions are
// allowed to redirect — see CLAUDE.md → Frontend Import Rules (rule 3).
export async function finishOnboarding() {
  redirect("/map");
}
