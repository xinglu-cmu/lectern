import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Lectern",
  description:
    "Know what your AI is reading: screen documents for hidden prompts, zone them by function, export clean Markdown.",
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
