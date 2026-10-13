"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useDailyTabs } from "@/components/client/daily-tabs";
import { dailyTabHref, type DailyTab } from "@/components/client/daily-tab-state";
import { isArchiveSnapshot, type ArchiveSnapshot } from "@/domain/archive";
import { isBusinessDate } from "@/domain/daily";
import { isStockSearchSnapshot, type StockSearchItem } from "@/domain/stocks";

const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

function koreanToday(): string {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function shiftMonth(value: string, amount: number): string {
  const [year, month] = value.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1 + amount, 1));
  return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}`;
}

function DateCalendar({ businessDate }: Readonly<{ businessDate: string }>) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [archive, setArchive] = useState<ArchiveSnapshot | null>(null);
  const [month, setMonth] = useState(isBusinessDate(businessDate) ? businessDate.slice(0, 7) : "2000-01");
  const [loading, setLoading] = useState(false);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    if (isBusinessDate(businessDate)) setMonth(businessDate.slice(0, 7));
  }, [businessDate]);

  async function openCalendar() {
    dialog.current?.showModal();
    if (archive || loading) return;
    setLoading(true);
    try {
      const response = await fetch("/api/archive?limit=100", { cache: "no-store" });
      const payload: unknown = response.ok ? await response.json() : null;
      if (!isArchiveSnapshot(payload)) throw new Error("invalid archive");
      setArchive(payload);
    } catch {
      setUnavailable(true);
    } finally {
      setLoading(false);
    }
  }

  const [year, monthNumber] = month.split("-").map(Number);
  const firstWeekday = new Date(Date.UTC(year, monthNumber - 1, 1)).getUTCDay();
  const dayCount = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  const cells: (number | null)[] = [
    ...Array.from({ length: firstWeekday }, () => null),
    ...Array.from({ length: dayCount }, (_, index) => index + 1),
  ];
  const dateRows = new Map(archive?.dates.map((row) => [row.business_date, row]) ?? []);
  const today = koreanToday();

  return (
    <>
      <button className="calendar-trigger" type="button" aria-label="기준일 달력" aria-haspopup="dialog" onClick={openCalendar}>
        <svg viewBox="0 0 20 20" aria-hidden="true" focusable="false">
          <rect x="3" y="4.5" width="14" height="13" rx="2" />
          <path d="M6 3v3M14 3v3M3.5 8h13" />
        </svg>
      </button>
      <dialog className="public-calendar-dialog" aria-label="기준일 달력" ref={dialog}>
        <div className="public-calendar-title">
          <h2>기준일 선택</h2>
          <form method="dialog"><button className="public-calendar-close" aria-label="달력 닫기">닫기</button></form>
        </div>
        <div className="date-calendar-head">
          <button className="nav-button" type="button" aria-label="이전 달" onClick={() => setMonth(shiftMonth(month, -1))}>이전</button>
          <strong>{year}년 {monthNumber}월</strong>
          <button className="nav-button" type="button" aria-label="다음 달" disabled={month >= today.slice(0, 7)} onClick={() => setMonth(shiftMonth(month, 1))}>다음</button>
        </div>
        <div className="public-calendar-grid" aria-label="날짜 선택">
          {WEEKDAYS.map((day) => <span className="public-calendar-weekday" key={day}>{day}</span>)}
          {cells.map((day, index) => {
            if (day === null) return <span className="public-calendar-empty" aria-hidden="true" key={`empty-${index}`} />;
            const date = `${month}-${String(day).padStart(2, "0")}`;
            const row = dateRows.get(date);
            const future = date > today;
            const active = date === businessDate;
            const label = row
              ? `${date}, 리포트 ${row.report_count}건, 뉴스 관찰 ${row.news_observation_count}건`
              : `${date}, 저장 자료 없음`;
            return (
              <button
                className={`public-calendar-day${row?.report_count ? " has-report" : " no-report"}${active ? " active" : ""}`}
                type="button"
                aria-label={label}
                aria-current={active ? "date" : undefined}
                disabled={future}
                key={date}
                onClick={() => window.location.assign(`/daily/${date}/main`)}
              >
                <b>{day}</b>
                {row?.report_count ? <small>{row.report_count}건</small> : null}
              </button>
            );
          })}
        </div>
        <p className="public-calendar-status" aria-live="polite">
          {loading ? "저장 날짜를 불러오는 중입니다." : unavailable ? "저장 건수를 불러오지 못했습니다. 날짜로 이동할 수 있습니다." : "저장 리포트와 뉴스 관찰 건수를 함께 표시합니다."}
        </p>
      </dialog>
    </>
  );
}

function StockSearch({ businessDate }: Readonly<{ businessDate: string }>) {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<StockSearchItem[]>([]);
  const [status, setStatus] = useState("선택일 저장 종목과 리포트를 검색합니다.");
  const [focused, setFocused] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  useEffect(() => {
    const search = query.trim();
    setActiveIndex(-1);
    if (search.length < 2) {
      setItems([]);
      setStatus("두 글자 이상 입력하면 저장 종목을 찾습니다.");
      return;
    }

    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setStatus("저장 종목 검색 중입니다.");
      try {
        const params = new URLSearchParams({ date: businessDate, q: search });
        const response = await fetch(`/api/stocks/search?${params}`, { cache: "no-store", signal: controller.signal });
        const payload: unknown = response.ok ? await response.json() : null;
        if (!isStockSearchSnapshot(payload, businessDate, search)) throw new Error("invalid stock search");
        const results = payload.items.slice(0, 8);
        setItems(results);
        setStatus(results.length ? `저장 종목 ${results.length}건` : payload.empty_state ?? "저장 종목이 없습니다.");
      } catch {
        if (!controller.signal.aborted) {
          setItems([]);
          setStatus("저장 종목 검색을 불러오지 못했습니다.");
        }
      }
    }, 250);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [businessDate, query]);

  function selectStock(item: StockSearchItem) {
    window.location.assign(`/daily/${businessDate}/stocks?stock=${item.stock_code}#selected-stock`);
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === "ArrowDown" && items.length) {
      event.preventDefault();
      setActiveIndex((index) => (index + 1) % items.length);
    } else if (event.key === "ArrowUp" && items.length) {
      event.preventDefault();
      setActiveIndex((index) => (index <= 0 ? items.length - 1 : index - 1));
    } else if (event.key === "Enter" && items[activeIndex]) {
      event.preventDefault();
      selectStock(items[activeIndex]);
    } else if (event.key === "Escape") {
      setFocused(false);
      setActiveIndex(-1);
    }
  }

  return (
    <form className="public-search" action={`/daily/${businessDate}/stocks`} method="get" role="search">
      <div className="public-search-box">
        <label className="sr-only" htmlFor="public-stock-search">저장 종목 검색</label>
        <input
          id="public-stock-search"
          name="q"
          type="search"
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={focused && items.length > 0}
          aria-controls="public-stock-search-results"
          aria-activedescendant={activeIndex >= 0 ? `stock-search-option-${activeIndex}` : undefined}
          placeholder="저장 종목명 또는 코드"
          autoComplete="off"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setTimeout(() => setFocused(false), 120)}
          onKeyDown={handleKeyDown}
        />
        {focused && query.trim().length >= 2 ? <div className="public-search-results" id="public-stock-search-results" role="listbox" aria-label="저장 종목 검색 결과">
          {items.length ? items.map((item, index) => (
            <button
              id={`stock-search-option-${index}`}
              className="public-search-result"
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              key={item.stock_code}
              onMouseDown={(event) => event.preventDefault()}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => selectStock(item)}
            >
              <b>{item.stock_name} ({item.stock_code})</b>
              <span>{item.market ?? "시장 자료 없음"} · {item.display_status}</span>
            </button>
          )) : <p className="public-search-empty" role="status">{status}</p>}
        </div> : null}
      </div>
      <p className="public-search-status" aria-live="polite">{status}</p>
    </form>
  );
}

export default function PublicHeader({ businessDate }: Readonly<{ businessDate: string }>) {
  const { activeTab, canSwitchTabs, selectTab } = useDailyTabs();
  const pathname = usePathname();
  const searchParams = useSearchParams().toString();
  const search = searchParams ? `?${searchParams}` : "";
  const datePath = `/daily/${businessDate}`;
  function handleTabClick(event: React.MouseEvent<HTMLAnchorElement>, tab: DailyTab) {
    if (!canSwitchTabs) return;
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    selectTab(tab);
  }

  return (
    <header className="public-header">
      <div className="public-brand-column">
        <div className="public-brand-row">
          <Link className="public-brand" href={`${datePath}/main`} prefetch={false}>KR-Stock</Link>
          <div className="public-date-picker">
            <DateCalendar businessDate={businessDate} />
          </div>
        </div>
      <p className="public-header-subtitle">일일 리포트 (<time>{businessDate}</time>) · <Link href="/archive" prefetch={false}>아카이브</Link></p>
      </div>
      <div className="public-header-tools">
        <StockSearch businessDate={businessDate} />
        <nav className="top-tabs" aria-label="상단 탭">
          <Link id="daily-main-tab" className={`top-tab${activeTab === "main" ? " active" : ""}`} href={dailyTabHref(businessDate, "main", search, pathname)} prefetch={false} aria-current={activeTab === "main" ? "page" : undefined} onClick={(event) => handleTabClick(event, "main")}>메인</Link>
          <Link id="daily-watch-tab" className={`top-tab${activeTab === "watch" ? " active" : ""}`} href={dailyTabHref(businessDate, "watch", search, pathname)} prefetch={false} aria-current={activeTab === "watch" ? "page" : undefined} onClick={(event) => handleTabClick(event, "watch")}>관찰</Link>
          <Link id="daily-stock-tab" className={`top-tab${activeTab === "stock" ? " active" : ""}`} href={dailyTabHref(businessDate, "stock", search, pathname)} prefetch={false} aria-current={activeTab === "stock" ? "page" : undefined} onClick={(event) => handleTabClick(event, "stock")}>종목</Link>
        </nav>
      </div>
    </header>
  );
}
