import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lectern",
  description:
    "A provenance-first reading workspace — every claim shows its source.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
