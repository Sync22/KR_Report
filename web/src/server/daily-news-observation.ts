import "server-only";

import type { DatabaseSync } from "node:sqlite";

type NewsRunRow = {
  run_id: string;
  stock_name: string;
  stock_code: string | null;
  matched_count: number;
  created_at: string;
};

type NewsEvidenceRow = {
  run_id: string;
  evidence_key: string;
  stock_code: string | null;
  stock_name: string;
  candidate_priority_presence: number;
  krx_reference_date: string | null;
  source_lane: string;
  title: string;
  url: string;
  canonical_url: string;
  published_at: string;
  relevance: string;
  sentiment: string;
  event_types_json: string;
  stock_impact: string;
  created_at: string;
  lineage_type: string;
};

type NewsEvidence = Omit<NewsEvidenceRow, "candidate_priority_presence" | "event_types_json"> & {
  candidate_priority_presence: boolean;
  event_types: string[];
};

type NewsObservationOptions = {
  limit?: number;
  stockCodes?: readonly string[] | null;
};

const evidenceColumns = `
  run_id, evidence_key, stock_code, stock_name, candidate_priority_presence,
  krx_reference_date, source_lane, title, url, canonical_url,
  published_at, relevance, sentiment,
  event_types_json, stock_impact, created_at, lineage_type
`;

export function buildNewsObservationSummaryFromDatabase(
  database: DatabaseSync,
  businessDate: string,
  options: NewsObservationOptions = {},
): Record<string, unknown> {
  const requestedCodes = (options.stockCodes ?? [])
    .map((stockCode) => String(stockCode).trim())
    .filter(Boolean);
  const requestedCodeSet = new Set(requestedCodes);
  const runs = database.prepare(`
    SELECT run_id, stock_name, stock_code, matched_count, created_at
    FROM news_intelligence_runs
    WHERE target_date = ?
    ORDER BY created_at DESC, run_id DESC
    LIMIT ?
  `).all(businessDate, 100) as unknown as NewsRunRow[];
  const runsByKey = new Map<string, NewsRunRow[]>();
  for (const run of runs) {
    if (requestedCodeSet.size && !requestedCodeSet.has(run.stock_code ?? "")) continue;
    const key = run.stock_code || run.stock_name;
    if (!key) continue;
    const grouped = runsByKey.get(key) ?? [];
    grouped.push(run);
    runsByKey.set(key, grouped);
  }

  const keys = requestedCodes.length ? requestedCodes : [...runsByKey.keys()];
  const representativeRuns: NewsRunRow[] = [];
  const evidenceRowsByKey = new Map<string, NewsEvidence[]>();
  const evidenceRows: NewsEvidence[] = [];
  const evidenceQuery = database.prepare(`
    SELECT ${evidenceColumns}
    FROM report_linked_news_evidence
    WHERE run_id = ?
    ORDER BY target_date DESC, created_at DESC, evidence_key
    LIMIT ?
  `);
  for (const key of keys.slice(0, Math.max(options.limit ?? 3, 1))) {
    const groupedRuns = runsByKey.get(key) ?? [];
    if (!groupedRuns.length) continue;
    const representativeRun = latestRun(groupedRuns);
    representativeRuns.push(representativeRun);
    const rows = uniqueEvidenceRows(groupedRuns.flatMap((run) =>
      (evidenceQuery.all(run.run_id, 100) as unknown as NewsEvidenceRow[]).map(toNewsEvidence)
    ));
    evidenceRows.push(...rows);
    evidenceRowsByKey.set(key, rows);
  }

  const uniqueEvidence = uniqueEvidenceRows(evidenceRows);
  if (!representativeRuns.length) {
    return {
      source: "stored_news_intelligence_observation",
      read_only: true,
      live_fetch: false,
      available: false,
      business_date: businessDate,
      display_label: "뉴스 근거 수집 전",
      reason: "저장 뉴스 근거를 아직 수집하지 않았습니다.",
      connection_note: "저장 뉴스 근거가 수집되면 우선 확인 후보와 연결됩니다.",
      candidate_overlap_count: 0,
      candidate_overlap_names: [],
      direct_count: 0,
      caution_count: 0,
      market_context_count: 0,
      krx_reference_status: "missing",
      observed_at: null,
      top_titles: [],
      items: [],
      empty_state: "뉴스 근거 수집 전",
      missing_context: ["stored_news_observation"],
      connection_label: "뉴스 근거 수집 전",
      connection_reason: "저장 뉴스 근거가 수집되면 우선 확인 후보와 연결됩니다.",
    };
  }

  const independentRows = uniqueEvidence.filter((row) => row.lineage_type === "independent");
  const reportRecapCount = uniqueEvidence.filter((row) => row.lineage_type === "report_recap").length;
  const directCount = uniqueEvidence.filter((row) => row.relevance === "direct").length;
  const cautionCount = uniqueEvidence.filter(isCaution).length;
  const positiveDirectCount = positiveDirectCountFor(uniqueEvidence);
  const primaryCautionCount = primaryCautionCountFor(uniqueEvidence);
  const marketContextCount = uniqueEvidence.filter((row) => row.relevance === "market_context").length;
  const krxReferenceStatus = krxStatus(uniqueEvidence, businessDate);
  let [evidenceDirection, evidenceDirectionReason] = direction({
    directCount,
    positiveDirectCount,
    primaryCautionCount,
  });
  const candidateOverlapNames = requestedCodeSet.size
    ? uniqueTexts(uniqueEvidence
      .filter((row) => row.stock_code !== null && requestedCodeSet.has(row.stock_code))
      .map((row) => row.stock_name), 3)
    : candidateOverlapNamesFor(uniqueEvidence, 3);
  const topTitles = uniqueTexts(uniqueEvidence.map((row) => row.title), 3);
  const items = representativeRuns.map((run) => {
    const key = run.stock_code || run.stock_name;
    return observationSummaryItem(
      run,
      evidenceRowsByKey.get(key) ?? [],
      businessDate,
      runsByKey.get(key) ?? [],
    );
  });

  let displayLabel: string;
  let reason: string;
  let connectionLabel: string;
  let connectionReason: string;
  let connectionNote: string;
  if (!uniqueEvidence.length) {
    displayLabel = "뉴스 수집 완료";
    reason = "5-lane 뉴스 수집은 완료됐지만 우선 후보와 매칭된 기사는 없습니다.";
    connectionLabel = "매칭 뉴스 없음";
    connectionReason = "수집은 실행됐고, 선택 날짜의 후보와 직접 연결된 뉴스는 없었습니다.";
    connectionNote = "뉴스 수집 결과 매칭 0건입니다.";
  } else {
    [displayLabel, reason] = observationConnection({
      directCount,
      cautionCount,
      positiveDirectCount,
      primaryCautionCount,
      marketContextCount,
    });
    if (!independentRows.length && reportRecapCount) {
      displayLabel = "리포트 재인용 매칭";
      reason = `후보와 연결된 리포트 재인용 뉴스 ${reportRecapCount}건이 저장돼 있습니다.`;
      evidenceDirection = "리포트 재인용 흐름";
      evidenceDirectionReason = "리포트 내용을 재인용한 뉴스 흐름이며 별도 독립 근거로 중복 계산하지 않습니다.";
    } else if (!independentRows.length) {
      displayLabel = "종목 뉴스 매칭";
      reason = `후보와 직접 매칭된 뉴스 ${uniqueEvidence.length}건이 저장돼 있으며 출처 계보는 확인 전입니다.`;
      evidenceDirection = "출처 계보 확인 전";
      evidenceDirectionReason = "종목 매칭은 확인됐고 독립 원출처 여부는 별도 메타데이터로 남깁니다.";
    }
    connectionLabel = displayLabel;
    connectionReason = reason;
    connectionNote = candidateOverlapNames.length
      ? `우선 확인 후보와 겹친 뉴스 근거: ${candidateOverlapNames.join(", ")}`
      : "우선 확인 후보와 함께 읽는 뉴스 근거입니다.";
  }

  return {
    source: "stored_news_intelligence_observation",
    read_only: true,
    live_fetch: false,
    available: true,
    business_date: businessDate,
    display_label: displayLabel,
    reason,
    connection_note: connectionNote,
    candidate_overlap_count: candidateOverlapNames.length,
    candidate_overlap_names: candidateOverlapNames,
    direct_count: directCount,
    positive_direct_count: positiveDirectCount,
    primary_caution_count: primaryCautionCount,
    caution_count: cautionCount,
    market_context_count: marketContextCount,
    independent_count: independentRows.length,
    report_recap_count: reportRecapCount,
    unknown_count: uniqueEvidence.filter((row) => !["independent", "report_recap"].includes(row.lineage_type)).length,
    krx_reference_status: krxReferenceStatus,
    observed_at: latestIso([...uniqueEvidence.map((row) => row.created_at), ...representativeRuns.map((run) => run.created_at)]),
    evidence_direction: evidenceDirection,
    evidence_direction_reason: evidenceDirectionReason,
    top_titles: topTitles,
    items,
    missing_context: [],
    connection_label: connectionLabel,
    connection_reason: connectionReason,
  };
}

function toNewsEvidence(row: NewsEvidenceRow): NewsEvidence {
  return {
    ...row,
    candidate_priority_presence: Boolean(row.candidate_priority_presence),
    event_types: JSON.parse(row.event_types_json) as string[],
  };
}

function latestRun(runs: NewsRunRow[]): NewsRunRow {
  return runs.reduce((latest, run) =>
    compareDateTimes(run.created_at, latest.created_at) > 0 ||
    (compareDateTimes(run.created_at, latest.created_at) === 0 && run.run_id > latest.run_id)
      ? run
      : latest
  );
}

function uniqueEvidenceRows(rows: NewsEvidence[]): NewsEvidence[] {
  const latestByKey = new Map<string, NewsEvidence>();
  for (const row of rows) {
    const key = row.canonical_url || row.evidence_key || row.url || `${row.stock_code ?? "None"}:${row.title}:${row.published_at}`;
    const previous = latestByKey.get(key);
    if (!previous || compareDateTimes(row.created_at, previous.created_at) > 0 ||
      (compareDateTimes(row.created_at, previous.created_at) === 0 && row.run_id > previous.run_id)) {
      latestByKey.set(key, row);
    }
  }
  return [...latestByKey.values()];
}

function observationSummaryItem(
  run: NewsRunRow,
  rows: NewsEvidence[],
  businessDate: string,
  collectionRuns: NewsRunRow[],
): Record<string, unknown> {
  const collectionState = collectionStateFor(collectionRuns.length ? collectionRuns : [run], rows);
  if (!rows.length) {
    return {
      ...collectionState,
      available: true,
      stock_name: run.stock_name,
      stock_code: run.stock_code,
      display_label: "매칭 뉴스 없음",
      reason: "수집은 완료됐지만 이 후보와 직접 연결된 뉴스는 없었습니다.",
      direct_count: 0,
      caution_count: 0,
      market_context_count: 0,
      krx_reference_status: "missing",
      observed_at: run.created_at,
      top_title: null,
      connection_label: "매칭 뉴스 없음",
      connection_reason: "수집은 실행됐고, 선택 날짜의 후보와 직접 연결된 뉴스는 없었습니다.",
    };
  }
  const badge = candidateNewsBadge(rows, businessDate);
  return {
    available: Boolean(badge.available),
    stock_name: run.stock_name,
    stock_code: run.stock_code,
    display_label: badge.display_label,
    reason: badge.reason,
    direct_count: badge.direct_count,
    positive_direct_count: badge.positive_direct_count,
    primary_caution_count: badge.primary_caution_count,
    caution_count: badge.caution_count,
    market_context_count: badge.market_context_count,
    independent_count: badge.independent_count,
    report_recap_count: badge.report_recap_count,
    unknown_count: badge.unknown_count,
    krx_reference_status: badge.krx_reference_status,
    observed_at: latestIso([run.created_at, ...rows.map((row) => row.created_at)]),
    evidence_direction: badge.evidence_direction,
    evidence_direction_reason: badge.evidence_direction_reason,
    top_title: badge.top_title,
    connection_label: badge.connection_label,
    connection_reason: badge.connection_reason,
    ...collectionState,
  };
}

function collectionStateFor(runs: NewsRunRow[], rows: NewsEvidence[]): Record<string, unknown> {
  if (!runs.length) {
    return {
      collection_run_count: 0,
      latest_collection_at: null,
      latest_collection_status: "not_collected",
      daily_evidence_retained: false,
    };
  }
  const latest = latestRun(runs);
  const status = Number(latest.matched_count || 0) > 0 ? "matched" : "no_match";
  return {
    collection_run_count: runs.length,
    latest_collection_at: latest.created_at,
    latest_collection_status: status,
    daily_evidence_retained: status === "no_match" && Boolean(rows.length),
  };
}

function candidateNewsBadge(rows: NewsEvidence[], businessDate: string): Record<string, unknown> {
  const uniqueRows = uniqueEvidenceRows(rows);
  const independentRows = uniqueRows.filter((row) => row.lineage_type === "independent");
  const directCount = uniqueRows.filter((row) => row.relevance === "direct").length;
  const cautionCount = uniqueRows.filter(isCaution).length;
  const positiveDirectCount = positiveDirectCountFor(uniqueRows);
  const primaryCautionCount = primaryCautionCountFor(uniqueRows);
  const marketContextCount = uniqueRows.filter((row) => row.relevance === "market_context").length;
  const independentCount = independentRows.length;
  const reportRecapCount = uniqueRows.filter((row) => row.lineage_type === "report_recap").length;
  const unknownCount = uniqueRows.length - independentCount - reportRecapCount;
  const krxReferenceStatus = krxStatus(uniqueRows, businessDate);
  let [evidenceDirection, evidenceDirectionReason] = direction({ directCount, positiveDirectCount, primaryCautionCount });
  let [connectionLabel, connectionReason] = observationConnection({
    directCount,
    cautionCount,
    positiveDirectCount,
    primaryCautionCount,
    marketContextCount,
  });
  if (!independentRows.length && reportRecapCount) {
    connectionLabel = "리포트 재인용 매칭";
    connectionReason = `후보와 연결된 리포트 재인용 뉴스 ${reportRecapCount}건이 저장돼 있습니다.`;
    evidenceDirection = "리포트 재인용 흐름";
    evidenceDirectionReason = "리포트 내용을 재인용한 뉴스 흐름이며 별도 독립 근거로 중복 계산하지 않습니다.";
  } else if (!independentRows.length) {
    connectionLabel = "종목 뉴스 매칭";
    connectionReason = `후보와 직접 매칭된 뉴스 ${uniqueRows.length}건이 저장돼 있으며 출처 계보는 확인 전입니다.`;
    evidenceDirection = "출처 계보 확인 전";
    evidenceDirectionReason = "종목 매칭은 확인됐고 독립 원출처 여부는 별도 메타데이터로 남깁니다.";
  }
  const orderedRows = [...uniqueRows].sort((left, right) =>
    relevanceOrder(left) - relevanceOrder(right) ||
    compareDateTimes(left.created_at, right.created_at) ||
    compareStrings(left.title, right.title)
  );
  const topTitle = uniqueTexts(orderedRows.map((row) => row.title), 1)[0] ?? null;
  return {
    available: true,
    display_label: connectionLabel,
    reason: topTitle || "저장 뉴스 observation이 같은 후보와 연결됩니다.",
    direct_count: directCount,
    positive_direct_count: positiveDirectCount,
    primary_caution_count: primaryCautionCount,
    caution_count: cautionCount,
    market_context_count: marketContextCount,
    independent_count: independentCount,
    report_recap_count: reportRecapCount,
    unknown_count: unknownCount,
    krx_reference_status: krxReferenceStatus,
    evidence_direction: evidenceDirection,
    evidence_direction_reason: evidenceDirectionReason,
    top_title: topTitle,
    connection_label: connectionLabel,
    connection_reason: connectionReason,
  };
}

function isCaution(row: NewsEvidence): boolean {
  return ["Caution", "Negative", "Mixed"].includes(row.sentiment) ||
    ["Caution", "Negative", "Strong Negative"].includes(row.stock_impact) ||
    row.event_types.includes("Risk/Caution");
}

function positiveDirectCountFor(rows: NewsEvidence[]): number {
  return rows.filter((row) =>
    !(row.source_lane === "top2_search" && row.lineage_type !== "independent") &&
    row.relevance === "direct" &&
    (row.sentiment === "Positive" || ["Positive", "Strong Positive"].includes(row.stock_impact))
  ).length;
}

function primaryCautionCountFor(rows: NewsEvidence[]): number {
  return rows.filter((row) =>
    !(row.source_lane === "top2_search" && row.lineage_type !== "independent") &&
    row.relevance === "direct" && isCaution(row)
  ).length;
}

function direction({
  directCount,
  positiveDirectCount,
  primaryCautionCount,
}: {
  directCount: number;
  positiveDirectCount: number;
  primaryCautionCount: number;
}): [string, string] {
  if (positiveDirectCount > 0 && primaryCautionCount > 0) {
    return [
      "직접 근거 상충",
      `직접 긍정 뉴스 ${positiveDirectCount}건과 직접 주의 뉴스 ${primaryCautionCount}건이 함께 있습니다.`,
    ];
  }
  if (positiveDirectCount > 0) {
    return ["상승 근거 우세", `직접 긍정 뉴스 ${positiveDirectCount}건이 직접 주의 뉴스보다 우세합니다.`];
  }
  if (primaryCautionCount > 0) {
    return ["하방 위험 우세", `직접 주의 뉴스 ${primaryCautionCount}건이 있어 리포트 근거를 다시 확인합니다.`];
  }
  if (directCount > 0) {
    return ["직접 근거 중립", `직접 연결 뉴스 ${directCount}건은 있으나 방향 근거가 분명하지 않습니다.`];
  }
  return ["직접 근거 부족", "후보와 직접 연결된 방향 근거가 아직 부족합니다."];
}

function krxStatus(rows: NewsEvidence[], businessDate: string): string {
  const dates = rows.map((row) => row.krx_reference_date).filter((value): value is string => value !== null);
  if (dates.includes(businessDate)) return "exact";
  return dates.length ? "stale" : "missing";
}

function candidateOverlapNamesFor(rows: NewsEvidence[], limit: number): string[] {
  const names: string[] = [];
  const seen = new Set<string>();
  for (const row of rows) {
    if (!row.candidate_priority_presence) continue;
    const key = row.stock_code || row.stock_name;
    if (seen.has(key)) continue;
    seen.add(key);
    names.push(row.stock_name || row.stock_code || "-");
    if (names.length >= Math.max(limit, 0)) break;
  }
  return names;
}

function observationConnection({
  directCount,
  cautionCount,
  positiveDirectCount,
  primaryCautionCount,
  marketContextCount,
}: {
  directCount: number;
  cautionCount: number;
  positiveDirectCount: number;
  primaryCautionCount: number;
  marketContextCount: number;
}): [string, string] {
  if (primaryCautionCount > 0 && positiveDirectCount <= 0) {
    return ["주의 뉴스 매칭", "주의/혼합 성격의 뉴스가 후보와 직접 매칭됐습니다."];
  }
  if (directCount > 0) return ["종목 뉴스 매칭", `후보와 직접 매칭된 뉴스 ${directCount}건이 저장돼 있습니다.`];
  if (cautionCount > 0) return ["주의 뉴스 매칭", "주의/혼합 성격의 뉴스가 후보와 매칭됐습니다."];
  if (marketContextCount > 0) return ["시장 맥락 참고", "업종/시장 맥락 뉴스라 종목 직접 근거로 과신하지 않습니다."];
  return ["관련 뉴스 매칭", "후보와 간접 연결된 저장 뉴스가 있습니다."];
}

function uniqueTexts(values: string[], limit: number): string[] {
  const result: string[] = [];
  const seen = new Set<string>();
  for (const value of values) {
    const text = value.trim();
    if (!text || seen.has(text)) continue;
    seen.add(text);
    result.push(text);
    if (result.length >= Math.max(limit, 0)) break;
  }
  return result;
}

function relevanceOrder(row: NewsEvidence): number {
  if (row.relevance === "direct") return 0;
  if (row.relevance === "indirect") return 1;
  return 2;
}

function latestIso(values: string[]): string {
  return values.reduce((latest, value) => compareDateTimes(value, latest) > 0 ? value : latest);
}

function compareDateTimes(left: string, right: string): number {
  return Date.parse(left) - Date.parse(right);
}

function compareStrings(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}
