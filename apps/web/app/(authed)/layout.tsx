"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";
import { useGetCurrentUser } from "@/__generated__/backend-client/users";
import Nav from "../Nav";

export default function AuthedLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading } = useGetCurrentUser({
    query: { retry: false },
  });

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return <div className="auth-loading">Loading</div>;
  }

  return (
    <>
      <Nav />
      {children}
    </>
  );
}
