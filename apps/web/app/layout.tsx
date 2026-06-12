import type { Metadata } from "next";
import type { ReactNode } from "react";
// Global stylesheets (BEM). theme.css first so its custom properties are defined
// before main.css consumes them. Replaces the imports in the old Layout.astro.
import "@/styles/theme.css";
import "@/styles/main.css";

export const metadata: Metadata = {
  title: "Hexagone",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Architects+Daughter&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
