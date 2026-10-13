import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Stock Monitor",
  description: "저장된 종목 리서치 아카이브",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
