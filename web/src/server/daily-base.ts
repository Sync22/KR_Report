import "server-only";

import type { DatabaseSync } from "node:sqlite";

type CategoryType = "sector" | "theme";
type MappingSource = "dated_snapshot" | "latest_mapping_fallback";

type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
  target_price_min: number | null;
  target_price_max: number | null;
  dominant_opinion: string | null;
};

type MarketReferenceRow = {
  business_date: string;
  stock_code: string;
  market: string;
  close_price: number | null;
  change_percent: number | null;
  volume: number | null;
  turnover: number | null;
  fetched_at: string;
};

type CategoryRollup = {
  business_date: string;
  category_type: CategoryType;
  category_key: string;
  display_name: string;
  stock_count: number;
  report_count: number;
  snapshot_date: string | null;
  mapping_source: MappingSource;
  category_code: string | null;
};

function dailySummaries(database: DatabaseSync, businessDate: string): SummaryRow[] {
  return database.prepare(`
    SELECT business_date, stock_name, stock_code, mention_count, broker_display,
           target_price_min, target_price_max, dominant_opinion
    FROM daily_stock_summaries
    WHERE business_date = ?
    ORDER BY mention_count DESC, stock_name ASC
  `).all(businessDate) as unknown as SummaryRow[];
}

function disabledCategoryIdentifiers(database: DatabaseSync, type: CategoryType): Set<string> {
  const rows = database.prepare(`
    SELECT category_key, display_name
    FROM category_master
    WHERE category_type = ? AND enabled = 0
  `).all(type) as unknown as { category_key: string; display_name: string }[];
  return new Set(rows.flatMap((row) => [row.category_key, row.display_name]));
}

function categoryRollups(database: DatabaseSync, businessDate: string, type: CategoryType): CategoryRollup[] {
  const hasSnapshot = database.prepare(`
    SELECT 1 AS present
    FROM category_membership_snapshots
    WHERE category_type = ? AND snapshot_date <= ?
    LIMIT 1
  `).get(type, businessDate);

  if (hasSnapshot) {
    const rows = database.prepare(`
      WITH latest_snapshots AS (
        SELECT cms.display_name, MAX(cms.snapshot_date) AS snapshot_date
        FROM category_membership_snapshots cms
        JOIN category_master cm
          ON cm.category_type = cms.category_type
         AND cm.category_key = cms.category_key
        WHERE cms.category_type = ? AND cms.snapshot_date <= ? AND cm.enabled = 1
        GROUP BY cms.display_name
      ),
      category_stock_rows AS (
        SELECT
          cms.display_name,
          cms.snapshot_date,
          COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
          MAX(dss.mention_count) AS mention_count
        FROM daily_stock_summaries dss
        JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
        JOIN latest_snapshots latest
          ON latest.display_name = cms.display_name
         AND latest.snapshot_date = cms.snapshot_date
        WHERE dss.business_date = ? AND cms.category_type = ?
        GROUP BY cms.display_name, cms.snapshot_date, COALESCE(dss.stock_code, dss.stock_name)
      )
      SELECT display_name, snapshot_date, COUNT(DISTINCT stock_identity) AS stock_count,
             COALESCE(SUM(mention_count), 0) AS report_count
      FROM category_stock_rows
      GROUP BY display_name, snapshot_date
      ORDER BY report_count DESC, stock_count DESC, display_name ASC
    `).all(type, businessDate, businessDate, type) as unknown as {
      display_name: string;
      snapshot_date: string;
      stock_count: number;
      report_count: number;
    }[];
    return rows.map((row) => ({
      business_date: businessDate,
      category_type: type,
      category_key: row.display_name,
      display_name: row.display_name,
      stock_count: row.stock_count,
      report_count: row.report_count,
      snapshot_date: row.snapshot_date,
      mapping_source: "dated_snapshot",
      category_code: null,
    }));
  }

  const disabled = disabledCategoryIdentifiers(database, type);
  const rows = type === "sector"
    ? database.prepare(`
        WITH summary_with_sector AS (
          SELECT
            COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') AS display_name,
            NULLIF(TRIM(sm.sector_code), '') AS category_code,
            COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
            dss.mention_count
          FROM daily_stock_summaries dss
          LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
          WHERE dss.business_date = ?
        )
        SELECT display_name, MIN(category_code) AS category_code,
               COUNT(DISTINCT stock_identity) AS stock_count,
               COALESCE(SUM(mention_count), 0) AS report_count
        FROM summary_with_sector
        GROUP BY display_name
        ORDER BY report_count DESC, stock_count DESC, display_name ASC
      `).all(businessDate) as unknown as {
        display_name: string;
        category_code: string | null;
        stock_count: number;
        report_count: number;
      }[]
    : database.prepare(`
        WITH theme_stock_rows AS (
          SELECT
            COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) AS display_name,
            stm.theme_code AS category_code,
            COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
            MAX(dss.mention_count) AS mention_count
          FROM daily_stock_summaries dss
          JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
          WHERE dss.business_date = ?
          GROUP BY COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code),
                   COALESCE(dss.stock_code, dss.stock_name)
        )
        SELECT MIN(category_code) AS category_code, display_name,
               COUNT(DISTINCT stock_identity) AS stock_count,
               COALESCE(SUM(mention_count), 0) AS report_count
        FROM theme_stock_rows
        GROUP BY display_name
        ORDER BY report_count DESC, stock_count DESC, display_name ASC
      `).all(businessDate) as unknown as {
        display_name: string;
        category_code: string | null;
        stock_count: number;
        report_count: number;
      }[];

  return rows
    .filter((row) => !disabled.has(row.display_name) && !disabled.has(row.category_code || ""))
    .map((row) => ({
      business_date: businessDate,
      category_type: type,
      category_key: row.display_name,
      display_name: row.display_name,
      stock_count: row.stock_count,
      report_count: row.report_count,
      snapshot_date: null,
      mapping_source: "latest_mapping_fallback",
      category_code: row.category_code,
    }));
}

function categoryDisplayName(value: string, type: CategoryType): string {
  if (!value || value === "N/A") return type === "sector" ? "업종 미확인" : "테마 미확인";
  return value;
}

function publicCategoryId(item: CategoryRollup): string {
  return item.category_type + "|" + item.display_name + "|" + (item.snapshot_date || "fallback");
}

function categoryRows(items: CategoryRollup[], type: CategoryType): Record<string, unknown>[] {
  return items.map((item) => type === "sector" ? {
    business_date: item.business_date,
    sector_name: item.display_name,
    sector_display_name: categoryDisplayName(item.display_name, type),
    sector_code: null,
    category_key: item.category_key,
    display_name: item.display_name,
    public_category_id: publicCategoryId(item),
    stock_count: item.stock_count,
    report_count: item.report_count,
    snapshot_date: item.snapshot_date,
    mapping_source: item.mapping_source,
  } : {
    business_date: item.business_date,
    theme_code: null,
    theme_name: item.display_name,
    theme_display_name: categoryDisplayName(item.display_name, type),
    category_key: item.category_key,
    display_name: item.display_name,
    public_category_id: publicCategoryId(item),
    stock_count: item.stock_count,
    report_count: item.report_count,
    snapshot_date: item.snapshot_date,
    mapping_source: item.mapping_source,
  });
}

function categoryMapping(database: DatabaseSync, businessDate: string): {
  mapping_basis: MappingSource;
  sector_snapshot_date: string | null;
  theme_snapshot_date: string | null;
} {
  const rows = database.prepare(`
    SELECT cms.category_type, MAX(cms.snapshot_date) AS snapshot_date
    FROM category_membership_snapshots cms
    JOIN category_master cm
      ON cm.category_type = cms.category_type
     AND cm.category_key = cms.category_key
    WHERE cms.category_type IN ('sector', 'theme')
      AND cms.snapshot_date <= ?
      AND cm.enabled = 1
    GROUP BY cms.category_type
  `).all(businessDate) as unknown as { category_type: CategoryType; snapshot_date: string }[];
  const snapshots = new Map(rows.map((row) => [row.category_type, row.snapshot_date]));
  const sectorDate = snapshots.get("sector") || null;
  const themeDate = snapshots.get("theme") || null;
  const dated = Boolean(sectorDate && themeDate);
  return {
    mapping_basis: dated ? "dated_snapshot" : "latest_mapping_fallback",
    sector_snapshot_date: sectorDate,
    theme_snapshot_date: themeDate,
  };
}

function categoryContract(
  categories: CategoryRollup[],
  mapping: ReturnType<typeof categoryMapping>,
): { mapping_basis: MappingSource; dated_snapshots_available: boolean; snapshot_dates: string[]; notice: string } {
  let snapshotDates = [...new Set(categories.flatMap((item) => item.snapshot_date ? [item.snapshot_date] : []))]
    .sort()
    .reverse();
  if (!snapshotDates.length && mapping.mapping_basis === "dated_snapshot") {
    snapshotDates = [mapping.sector_snapshot_date, mapping.theme_snapshot_date]
      .filter((value): value is string => !!value)
      .sort()
      .reverse();
  }
  if (snapshotDates.length) {
    return {
      mapping_basis: "dated_snapshot",
      dated_snapshots_available: true,
      snapshot_dates: snapshotDates,
      notice: "업종/테마는 선택 날짜 이하의 가장 가까운 저장 스냅샷 기준입니다. 실시간 갱신이나 확정 판단은 포함하지 않습니다.",
    };
  }
  return {
    mapping_basis: "latest_mapping_fallback",
    dated_snapshots_available: false,
    snapshot_dates: [],
    notice: "선택 날짜 이전의 카테고리 스냅샷이 없어 최신 저장 분류 기준으로 표시합니다.",
  };
}

function categoryIdentities(database: DatabaseSync, businessDate: string, items: CategoryRollup[]): Map<string, string[]> {
  const names = [...new Set(items.map((item) => item.display_name).filter(Boolean))].sort();
  if (!names.length) return new Map();
  const type = items[0].category_type;
  const placeholders = names.map(() => "?").join(", ");
  const dated = items.some((item) => item.mapping_source === "dated_snapshot" && item.snapshot_date !== null);
  const rows = dated
    ? database.prepare(`
        WITH latest_snapshots AS (
          SELECT cms.display_name, MAX(cms.snapshot_date) AS snapshot_date
          FROM category_membership_snapshots cms
          JOIN category_master cm
            ON cm.category_type = cms.category_type
           AND cm.category_key = cms.category_key
          WHERE cms.category_type = ?
            AND cms.display_name IN (${placeholders})
            AND cms.snapshot_date <= ?
            AND cm.enabled = 1
          GROUP BY cms.display_name
        )
        SELECT DISTINCT cms.display_name,
               COALESCE(dss.stock_code, dss.stock_name) AS stock_identity
        FROM daily_stock_summaries dss
        JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
        JOIN latest_snapshots latest
          ON latest.display_name = cms.display_name
         AND latest.snapshot_date = cms.snapshot_date
        WHERE dss.business_date = ? AND cms.category_type = ?
        ORDER BY cms.display_name ASC, dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
      `).all(type, ...names, businessDate, businessDate, type) as unknown as {
        display_name: string;
        stock_identity: string | null;
      }[]
    : type === "sector"
      ? database.prepare(`
          SELECT DISTINCT
            COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') AS display_name,
            COALESCE(dss.stock_code, dss.stock_name) AS stock_identity
          FROM daily_stock_summaries dss
          LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
          WHERE dss.business_date = ?
            AND COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') IN (${placeholders})
          ORDER BY display_name ASC, dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
        `).all(businessDate, ...names) as unknown as {
          display_name: string;
          stock_identity: string | null;
        }[]
      : database.prepare(`
          SELECT DISTINCT
            COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) AS display_name,
            COALESCE(dss.stock_code, dss.stock_name) AS stock_identity
          FROM daily_stock_summaries dss
          JOIN stock_theme_memberships stm ON stm.stock_code = dss.stock_code
          WHERE dss.business_date = ?
            AND COALESCE(NULLIF(TRIM(stm.theme_name), ''), stm.theme_code) IN (${placeholders})
          ORDER BY display_name ASC, dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
        `).all(businessDate, ...names) as unknown as {
          display_name: string;
          stock_identity: string | null;
        }[];
  const identities = new Map<string, string[]>();
  for (const row of rows) {
    if (row.display_name && row.stock_identity) {
      const values = identities.get(row.display_name) || [];
      values.push(row.stock_identity);
      identities.set(row.display_name, values);
    }
  }
  return identities;
}

function categoryHint(item: CategoryRollup): Record<string, string | null> {
  return {
    category_type: item.category_type,
    category_label: item.category_type === "sector" ? "업종" : "테마",
    display_name: item.display_name,
    category_display_name: categoryDisplayName(item.display_name, item.category_type),
    public_category_id: publicCategoryId(item),
    snapshot_date: item.snapshot_date,
    mapping_source: item.mapping_source,
  };
}

function primaryCategories(
  database: DatabaseSync,
  businessDate: string,
  sectors: CategoryRollup[],
  themes: CategoryRollup[],
): Map<string, Record<string, string | null>> {
  const byStock = new Map<string, Record<string, string | null>>();
  for (const items of [sectors, themes]) {
    if (!items.length) continue;
    const identities = categoryIdentities(database, businessDate, items);
    for (const item of items) {
      const hint = categoryHint(item);
      for (const identity of identities.get(item.display_name) || []) {
        if (identity && !byStock.has(identity)) byStock.set(identity, hint);
      }
    }
  }
  return byStock;
}

function marketReferences(database: DatabaseSync, businessDate: string, summaries: SummaryRow[]): Map<string, MarketReferenceRow> {
  const codes = [...new Set(summaries
    .map((item) => item.stock_code)
    .filter((code): code is string => typeof code === "string" && !!code.trim())
    .map((code) => code.trim()))].sort();
  if (!codes.length) return new Map();
  const placeholders = codes.map(() => "?").join(", ");
  const rows = database.prepare(`
    SELECT business_date, stock_code, market, close_price, change_percent, volume, turnover, fetched_at
    FROM stock_market_daily
    WHERE business_date = ? AND source = ? AND stock_code IN (${placeholders})
    ORDER BY stock_code ASC
  `).all(businessDate, "toss_openapi", ...codes) as unknown as MarketReferenceRow[];
  return new Map(rows.map((item) => [item.stock_code, item]));
}

function marketReference(item: MarketReferenceRow | undefined): Record<string, string | number | null> | null {
  if (!item) return null;
  return {
    business_date: item.business_date,
    market: item.market,
    close_price: item.close_price,
    change_percent: item.change_percent,
    volume: item.volume,
    turnover: item.turnover,
    fetched_at: item.fetched_at,
  };
}

function marketMood(businessDate: string, summaries: SummaryRow[], sectors: CategoryRollup[]) {
  const activeSectors = sectors.filter((item) => item.display_name && item.display_name !== "N/A");
  const topSector = activeSectors[0];
  return {
    business_date: businessDate,
    total_reports: summaries.reduce((total, item) => total + item.mention_count, 0),
    stock_count: summaries.length,
    active_sector_count: activeSectors.length,
    top_sector_name: topSector?.display_name || null,
    top_sector_report_count: topSector?.report_count || 0,
    multi_report_stock_count: summaries.filter((item) => item.mention_count >= 2).length,
    target_price_stock_count: summaries.filter((item) => item.target_price_min !== null || item.target_price_max !== null).length,
  };
}

function watchCandidates(summaries: SummaryRow[]): Record<string, string | number | null>[] {
  return summaries
    .flatMap((item) => {
      const reasons: string[] = [];
      if (item.mention_count >= 2) reasons.push("리포트 " + item.mention_count + "건");
      if (item.target_price_min !== null || item.target_price_max !== null) reasons.push("목표가 있음");
      if (reasons.length < 2) return [];
      return [{
        stock_name: item.stock_name,
        stock_code: item.stock_code,
        mention_count: item.mention_count,
        target_price_min: item.target_price_min,
        target_price_max: item.target_price_max,
        dominant_opinion: item.dominant_opinion,
        reason: reasons.join(" · "),
      }];
    })
    .sort((a, b) =>
      b.mention_count - a.mention_count
      || (b.target_price_max || b.target_price_min || 0) - (a.target_price_max || a.target_price_min || 0)
      || (a.stock_name < b.stock_name ? 1 : a.stock_name > b.stock_name ? -1 : 0))
    .slice(0, 5);
}

export function buildDailyBaseSnapshot(database: DatabaseSync, businessDate: string) {
  const summaries = dailySummaries(database, businessDate);
  const sectors = categoryRollups(database, businessDate, "sector");
  const themes = categoryRollups(database, businessDate, "theme");
  const mapping = categoryMapping(database, businessDate);
  const contract = categoryContract([...sectors, ...themes], mapping);
  const references = marketReferences(database, businessDate, summaries);
  const primary = primaryCategories(database, businessDate, sectors, themes);
  return {
    report_count: summaries.reduce((total, item) => total + item.mention_count, 0),
    summary_stock_count: summaries.length,
    mapping_notice: contract.notice,
    category_contract: contract,
    stocks: summaries.map((item) => ({
      business_date: item.business_date,
      stock_name: item.stock_name,
      stock_code: item.stock_code,
      mention_count: item.mention_count,
      broker_display: item.broker_display,
      target_price_min: item.target_price_min,
      target_price_max: item.target_price_max,
      dominant_opinion: item.dominant_opinion,
      market_reference: marketReference(references.get(item.stock_code || "")),
      primary_category: primary.get(item.stock_code || item.stock_name) || null,
    })),
    sectors: categoryRows(sectors, "sector"),
    themes: categoryRows(themes, "theme"),
    market_mood: marketMood(businessDate, summaries, sectors),
    watch_candidates: watchCandidates(summaries),
  };
}
