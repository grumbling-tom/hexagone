"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTransition } from "react";

// `logout` is a server action supplied by the authed layout — it clears the
// session server-side and redirects, so routing/data access stay out of here.
export default function Nav({ logout }: { logout: () => Promise<void> }) {
  const pathname = usePathname();
  const [pending, startTransition] = useTransition();

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
        onClick={() => startTransition(() => logout())}
        disabled={pending}
      >
        Log out
      </button>
    </nav>
  );
}
