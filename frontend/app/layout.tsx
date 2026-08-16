import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "V.E.N.U.S Control Center",
  description: "Frontend command center for V.E.N.U.S grid telemetry, alerts, analytics, and predictions.",
};

const themeBootstrapScript = `
(() => {
  const fallbackTheme = "dark";

  try {
    const rawSettings = window.localStorage.getItem("venus_settings");
    const parsedSettings = rawSettings ? JSON.parse(rawSettings) : null;
    const theme = parsedSettings?.theme === "light" ? "light" : fallbackTheme;
    document.documentElement.dataset.theme = theme;
    document.documentElement.classList.toggle("dark", theme === "dark");
    document.documentElement.classList.toggle("light", theme === "light");
  } catch {
    document.documentElement.dataset.theme = fallbackTheme;
    document.documentElement.classList.add("dark");
    document.documentElement.classList.remove("light");
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className="h-full antialiased"
      data-theme="dark"
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeBootstrapScript }} />
      </head>
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
