import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "V.E.N.U.S Control Center",
  description: "Frontend command center for V.E.N.U.S grid telemetry, alerts, analytics, and predictions.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
