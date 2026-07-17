import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://gravekeeper.dev"),
  title: "GraveKeeper — find the agents nobody turned off",
  description:
    "GraveKeeper scans your cloud and SaaS accounts read-only, inventories every AI agent and automation, and flags the zombies: live credentials with no owner and no recent purpose.",
  keywords: [
    "zombie agents",
    "orphan AI agents",
    "non-human identities",
    "machine identity",
    "agent sprawl",
    "service account cleanup",
    "NHI security",
  ],
  openGraph: {
    title: "GraveKeeper — find the agents nobody turned off",
    description:
      "Scan your accounts read-only and see which AI agents and automations are still running with nobody watching them.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
