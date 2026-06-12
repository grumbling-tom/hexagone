"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useDeleteCurrentSession } from "@/__generated__/backend-client/user-sessions";

export default function Nav() {
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  const logout = useDeleteCurrentSession({
    mutation: {
      onSuccess: () => {
        queryClient.clear();
        router.replace("/login");
      },
    },
  });

  return (
    <nav className="nav">
      <Link href="/map" aria-current={pathname === "/map" ? "page" : undefined}>
        Map
      </Link>
      <Link
        href="/uploads"
        aria-current={pathname === "/uploads" ? "page" : undefined}
      >
        Uploads
      </Link>
      <button
        className="button nav__logout"
        type="button"
        onClick={() => logout.mutate()}
        disabled={logout.isPending}
      >
        Log out
      </button>
    </nav>
  );
}
