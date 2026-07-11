import type { Metadata } from "next";
import { IBM_Plex_Mono, IBM_Plex_Serif } from "next/font/google";
import "./globals.css";

const plexMono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const plexSerif = IBM_Plex_Serif({
  variable: "--font-serif",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: "VaulS.ai — ask your codebase",
  description: "Index a public GitHub repo and query it with hybrid BM25 + vector retrieval.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${plexMono.variable} ${plexSerif.variable} h-full`}>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
