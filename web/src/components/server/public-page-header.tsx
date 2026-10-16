import Link from "next/link";

type PublicPage = "archive" | "market";

export default function PublicPageHeader({ current }: Readonly<{ current: PublicPage }>) {
  return (
    <header className="public-page-header">
      <Link className="public-brand" href="/" prefetch={false}>KR-Stock</Link>
      <nav className="public-section-nav" aria-label="주요 화면">
        <Link href="/" prefetch={false}>일일 브리핑</Link>
        <Link href="/archive" prefetch={false} aria-current={current === "archive" ? "page" : undefined}>아카이브</Link>
        <Link href="/market" prefetch={false} aria-current={current === "market" ? "page" : undefined}>저장 시장</Link>
      </nav>
    </header>
  );
}
