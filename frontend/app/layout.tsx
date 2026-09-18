import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Switchyard",
  description: "Adaptive multi-model AI routing — research workstation.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
