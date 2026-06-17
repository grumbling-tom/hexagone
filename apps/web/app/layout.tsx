import type { Metadata } from "next";
import type { ReactNode } from "react";
// Global stylesheets (BEM). theme.css first so its custom properties are defined
// before main.css consumes them.
import "@/styles/theme.css";
import "@/styles/main.css";

// Favicon is provided by the app/icon.svg file convention — Next auto-emits the
// <link rel="icon"> with the correct type, so no `icons` entry is needed here.
export const metadata: Metadata = {
  title: "Hexagone",
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
