import "server-only";

import { readFileSync } from "node:fs";
import type { DatabaseSync } from "node:sqlite";
import { resolve } from "node:path";

import { isBusinessDate } from "../domain/daily.ts";
import type { RotationOverlaySnapshot } from "../domain/category-rotation.ts";
import { withReadOnlyDatabase } from "./sqlite.ts";

const DEFAULT_IMAGE = { width: 1376, height: 768 };
type RecordValue = Record<string, unknown>;
type Coordinate = { x: number; y: number; radius: number; label: string };
type Alias = { rotation_label: string; coordinate_display_name: string; mapping_basis: string };
type CategoryRollup = { display_name: string; stock_count: number; report_count: number; snapshot_date: string | null };
type SummaryRow = {
  business_date: string;
  stock_name: string;
  stock_code: string | null;
  mention_count: number;
  broker_display: string;
};
type MarketRow = {
  stock_code: string;
  market: string;
  close_price: number | null;
  change_percent: number | null;
  turnover: number | null;
};
type EtfRow = {
  etf_code: string;
  etf_name: string;
  close_price: number | null;
  change_percent: number | null;
  turnover: number | null;
  underlying_index_name: string | null;
};
type RotationCandidate = RotationOverlaySnapshot["highlights"][number]["candidate_stocks"][number];

function isRecord(value: unknown): value is RecordValue {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function readJson(path: string): RecordValue | null {
  try {
    const value: unknown = JSON.parse(readFileSync(path, "utf8"));
    return isRecord(value) ? value : null;
  } catch {
    return null;
  }
}

function configPath(): string {
  const root = resolve(process.cwd(), "..");
  const configured = process.env.STOCK_MONITOR_ROTATION_OVERLAY_COORDINATES_PATH?.trim();
  return resolve(root, configured || "data/rotation_overlay_coordinates.json");
}

function integerConfig(value: unknown, fallback: number): number {
  if (!value) return fallback;
  const number = typeof value === "number" ? value : typeof value === "string" && /^[+-]?\d+$/.test(value.trim()) ? Number(value) : Number.NaN;
  if (!Number.isFinite(number)) throw new Error("Invalid rotation image dimension");
  return Math.trunc(number);
}

function floatConfig(value: unknown): number | null {
  const number = typeof value === "number" ? value : typeof value === "string" && value.trim() ? Number(value) : Number.NaN;
  return Number.isFinite(number) ? number : null;
}

function loadImageAndCoordinates(path: string): { image: { width: number; height: number }; coordinates: Map<string, Coordinate> } {
  const payload = readJson(path);
  if (!payload) return { image: DEFAULT_IMAGE, coordinates: new Map() };
  const image = isRecord(payload.image) ? payload.image : {};
  const width = integerConfig(image.width || DEFAULT_IMAGE.width, DEFAULT_IMAGE.width);
  const height = integerConfig(image.height || DEFAULT_IMAGE.height, DEFAULT_IMAGE.height);
  const coordinates = new Map<string, Coordinate>();
  if (!Array.isArray(payload.coordinates)) return { image: { width, height }, coordinates };
  for (const item of payload.coordinates) {
    if (!isRecord(item)) continue;
    const displayName = String(item.display_name ?? "").trim();
    const x = floatConfig(item.x);
    const y = floatConfig(item.y);
    const radius = floatConfig(item.radius);
    if (!displayName || x === null || y === null || radius === null || x < 0 || y < 0 || radius <= 0) continue;
    coordinates.set(displayName, { x, y, radius, label: String(item.label ?? "").trim() || displayName });
  }
  return { image: { width, height }, coordinates };
}

function loadAliases(path: string): Map<string, Alias> {
  const aliases = new Map<string, Alias>();
  const payload = readJson(path);
  if (!payload || !Array.isArray(payload.aliases)) return aliases;
  for (const item of payload.aliases) {
    if (!isRecord(item)) continue;
    const status = String(item.status ?? "").trim().toLowerCase();
    if (status && status !== "active") continue;
    const type = String(item.category_type ?? "").trim();
    const displayName = String(item.category_display_name ?? "").trim();
    const coordinateName = String(item.coordinate_display_name ?? "").trim();
    if (!type || !displayName || !coordinateName) continue;
    aliases.set(`${type}\0${displayName}`, {
      rotation_label: String(item.rotation_label ?? "").trim() || displayName,
      coordinate_display_name: coordinateName,
      mapping_basis: String(item.mapping_basis ?? "").trim() || "manual_alias",
    });
  }
  return aliases;
}

function loadEtfMappings(path: string): Map<string, string[]> {
  const mappings = new Map<string, string[]>();
  const payload = readJson(path);
  if (!payload || !Array.isArray(payload.mappings)) return mappings;
  for (const item of payload.mappings) {
    if (!isRecord(item)) continue;
    const status = String(item.status ?? "").trim().toLowerCase();
    if (status && status !== "active") continue;
    const type = String(item.category_type ?? "").trim();
    const displayName = String(item.category_display_name ?? "").trim();
    if (!type || !displayName || !Array.isArray(item.etf_codes)) continue;
    const codes = item.etf_codes.map((code) => String(code).trim()).filter(Boolean);
    if (codes.length) mappings.set(`${type}\0${displayName}`, codes);
  }
  return mappings;
}

function categoryRollups(database: DatabaseSync, businessDate: string): CategoryRollup[] {
  const latest = database.prepare(`
    SELECT MAX(snapshot_date) AS snapshot_date
    FROM category_membership_snapshots
    WHERE category_type = ? AND snapshot_date <= ?
  `).get("sector", businessDate)?.snapshot_date;
  if (latest === null || latest === undefined) {
    const disabledRows = database.prepare(`
      SELECT category_key, display_name FROM category_master
      WHERE category_type = ? AND enabled = 0
    `).all("sector") as unknown as { category_key: string; display_name: string }[];
    const disabled = new Set(disabledRows.flatMap((row) => [row.category_key, row.display_name]));
    const rows = database.prepare(`
      WITH summary_with_sector AS (
        SELECT COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') AS display_name,
               NULLIF(TRIM(sm.sector_code), '') AS sector_code,
               COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
               dss.mention_count
        FROM daily_stock_summaries dss
        LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
        WHERE dss.business_date = ?
      )
      SELECT display_name, MIN(sector_code) AS sector_code,
             COUNT(DISTINCT stock_identity) AS stock_count,
             COALESCE(SUM(mention_count), 0) AS report_count
      FROM summary_with_sector
      GROUP BY display_name
      ORDER BY report_count DESC, stock_count DESC, display_name ASC
    `).all(businessDate) as unknown as { display_name: string; sector_code: string | null; stock_count: number; report_count: number }[];
    const grouped = new Map<string, CategoryRollup>();
    for (const row of rows) {
      if (disabled.has(row.display_name) || disabled.has(row.sector_code || "")) continue;
      const current = grouped.get(row.display_name) ?? { display_name: row.display_name, stock_count: 0, report_count: 0, snapshot_date: null };
      current.stock_count += row.stock_count;
      current.report_count += row.report_count;
      grouped.set(row.display_name, current);
    }
    return [...grouped.values()];
  }

  if (typeof latest !== "string") throw new Error("Invalid stored sector snapshot date");
  return database.prepare(`
    WITH latest_snapshots AS (
      SELECT cms.display_name, MAX(cms.snapshot_date) AS snapshot_date
      FROM category_membership_snapshots cms
      JOIN category_master cm
        ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
      WHERE cms.category_type = 'sector' AND cms.snapshot_date <= ? AND cm.enabled = 1
      GROUP BY cms.display_name
    ), category_stock_rows AS (
      SELECT cms.display_name, cms.snapshot_date,
             COALESCE(dss.stock_code, dss.stock_name) AS stock_identity,
             MAX(dss.mention_count) AS mention_count
      FROM daily_stock_summaries dss
      JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
      JOIN latest_snapshots latest
        ON latest.display_name = cms.display_name AND latest.snapshot_date = cms.snapshot_date
      WHERE dss.business_date = ? AND cms.category_type = 'sector'
      GROUP BY cms.display_name, cms.snapshot_date, COALESCE(dss.stock_code, dss.stock_name)
    )
    SELECT display_name, snapshot_date, COUNT(DISTINCT stock_identity) AS stock_count,
           COALESCE(SUM(mention_count), 0) AS report_count
    FROM category_stock_rows
    GROUP BY display_name, snapshot_date
    ORDER BY report_count DESC, stock_count DESC, display_name ASC
  `).all(businessDate, businessDate) as unknown as CategoryRollup[];
}

function summariesForDisplayName(database: DatabaseSync, businessDate: string, displayName: string): SummaryRow[] {
  const hasSnapshot = database.prepare(`
    SELECT 1 AS found FROM category_membership_snapshots
    WHERE category_type = 'sector' AND snapshot_date <= ? LIMIT 1
  `).get(businessDate);
  if (!hasSnapshot) {
    return database.prepare(`
      SELECT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count, dss.broker_display
      FROM daily_stock_summaries dss
      LEFT JOIN stock_metadata sm ON sm.stock_code = dss.stock_code
      WHERE dss.business_date = ?
        AND COALESCE(NULLIF(TRIM(sm.sector_name), ''), 'N/A') = ?
      ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
    `).all(businessDate, displayName) as unknown as SummaryRow[];
  }
  const latest = database.prepare(`
    SELECT MAX(cms.snapshot_date) AS snapshot_date
    FROM category_membership_snapshots cms
    JOIN category_master cm ON cm.category_type = cms.category_type AND cm.category_key = cms.category_key
    WHERE cms.category_type = 'sector' AND cms.display_name = ?
      AND cms.snapshot_date <= ? AND cm.enabled = 1
  `).get(displayName, businessDate)?.snapshot_date;
  if (typeof latest !== "string") return [];
  return database.prepare(`
    SELECT DISTINCT dss.business_date, dss.stock_name, dss.stock_code, dss.mention_count, dss.broker_display
    FROM daily_stock_summaries dss
    JOIN category_membership_snapshots cms ON cms.stock_code = dss.stock_code
    WHERE dss.business_date = ? AND cms.snapshot_date = ?
      AND cms.category_type = 'sector' AND cms.display_name = ?
    ORDER BY dss.mention_count DESC, dss.stock_name ASC, dss.stock_code ASC
  `).all(businessDate, latest, displayName) as unknown as SummaryRow[];
}

function nullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stockMarketReferences(database: DatabaseSync, businessDate: string, codes: string[]): Map<string, MarketRow> {
  if (!codes.length) return new Map();
  const placeholders = codes.map(() => "?").join(", ");
  const rows = database.prepare(`
    SELECT stock_code, market, close_price, change_percent, turnover
    FROM stock_market_daily
    WHERE business_date = ? AND source = ? AND stock_code IN (${placeholders})
    ORDER BY stock_code ASC
  `).all(businessDate, "toss_openapi", ...codes) as unknown as MarketRow[];
  return new Map(rows.map((row) => [row.stock_code, row]));
}

function roundHalfEven(value: number, digits: number): number {
  const factor = 10 ** digits;
  const scaled = value * factor;
  const lower = Math.floor(scaled);
  const fraction = scaled - lower;
  const rounded = Math.abs(fraction - 0.5) < Number.EPSILON * Math.max(1, Math.abs(scaled))
    ? (lower % 2 === 0 ? lower : lower + 1)
    : fraction < 0.5 ? lower : lower + 1;
  return rounded / factor;
}

function flowAmount(value: number): string {
  const absolute = Math.abs(value);
  if (absolute >= 1_000_000_000_000) return `${roundHalfEven(absolute / 1_000_000_000_000, 1).toFixed(1)}조`;
  if (absolute >= 100_000_000) return `${roundHalfEven(absolute / 100_000_000, 0).toFixed(0)}억`;
  return `${new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(absolute)}원`;
}

function brokerCount(value: string): number {
  return new Set(value.split(",").map((item) => item.trim().replace(/\(\d+\)$/, "").trim()).filter(Boolean)).size;
}

function rotationCandidateStocks(database: DatabaseSync, businessDate: string, displayName: string): RotationCandidate[] {
  const summaries = summariesForDisplayName(database, businessDate, displayName);
  const codes = [...new Set(summaries.map((item) => item.stock_code).filter((code): code is string => typeof code === "string" && !!code.trim()).map((code) => code.trim()))].sort();
  const references = stockMarketReferences(database, businessDate, codes);
  const ordered = summaries.map((item, index) => ({ item, index, reference: item.stock_code ? references.get(item.stock_code) : undefined }))
    .sort((left, right) => right.item.mention_count - left.item.mention_count
      || (right.reference?.turnover ?? -1) - (left.reference?.turnover ?? -1)
      || (left.item.stock_name < right.item.stock_name ? 1 : left.item.stock_name > right.item.stock_name ? -1 : left.index - right.index))
    .slice(0, 3);
  return ordered.map(({ item, reference }) => {
    const evidence = [`리포트 ${item.mention_count}건`];
    if (reference?.turnover !== null && reference?.turnover !== undefined) evidence.push(`거래대금 ${flowAmount(reference.turnover)}`);
    const count = brokerCount(item.broker_display);
    return {
      stock_code: item.stock_code,
      stock_name: item.stock_name,
      mention_count: item.mention_count,
      broker_count_label: count ? `증권사 ${count}곳` : "증권사 미확인",
      market: reference?.market ?? null,
      close_price: reference?.close_price ?? null,
      change_percent: reference?.change_percent ?? null,
      turnover: reference?.turnover ?? null,
      evidence_label: evidence.join(" · "),
    };
  });
}

function rotationCandidateEtfs(database: DatabaseSync, businessDate: string, codes: string[]): RotationCandidate[] {
  const normalized = [...new Set(codes.map((code) => code.trim()).filter(Boolean))].sort();
  if (!normalized.length) return [];
  const placeholders = normalized.map(() => "?").join(", ");
  const rows = database.prepare(`
    SELECT etf_code, etf_name, close_price, change_percent, turnover, underlying_index_name
    FROM etf_daily_snapshots
    WHERE business_date = ? AND source = ? AND etf_code IN (${placeholders})
    ORDER BY COALESCE(turnover, 0) DESC, etf_code ASC
  `).all(businessDate, "toss_openapi", ...normalized) as unknown as EtfRow[];
  return rows.slice(0, 3).map((item) => ({
    etf_code: item.etf_code,
    etf_name: item.etf_name,
    close_price: item.close_price,
    change_percent: item.change_percent,
    turnover: item.turnover,
    underlying_index_name: item.underlying_index_name,
    evidence_label: item.turnover === null ? "저장 ETF 참고" : `거래대금 ${flowAmount(item.turnover)}`,
  }));
}

export function parseRotationOverlayLimit(rawLimit: string | null): number {
  const parsed = rawLimit === null || rawLimit === "" ? 5 : Number(rawLimit);
  return Number.isInteger(parsed) ? Math.max(1, Math.min(parsed, 10)) : 5;
}

export function getRotationOverlaySnapshot(businessDate: string, limit = 5): RotationOverlaySnapshot {
  if (!isBusinessDate(businessDate)) throw new RangeError("Invalid rotation overlay date");
  if (!Number.isInteger(limit) || limit < 1 || limit > 10) throw new RangeError("Invalid rotation overlay limit");

  const coordinatesPath = configPath();
  const { image, coordinates } = loadImageAndCoordinates(coordinatesPath);
  const aliases = loadAliases(resolve(coordinatesPath, "..", "rotation_image_aliases.json"));
  const etfMappings = loadEtfMappings(resolve(coordinatesPath, "..", "rotation_etf_candidates.json"));

  return withReadOnlyDatabase((database) => {
    database.exec("BEGIN");
    try {
      const rollups = categoryRollups(database, businessDate).sort((left, right) =>
        right.report_count - left.report_count || right.stock_count - left.stock_count
        || (left.display_name < right.display_name ? 1 : left.display_name > right.display_name ? -1 : 0)
      );
      const highlights: RotationOverlaySnapshot["highlights"] = [];
      const seen = new Set<string>();
      for (const item of rollups) {
        const displayName = item.display_name || "";
        if (!displayName || seen.has(displayName)) continue;
        const alias = aliases.get(`sector\0${displayName}`);
        const coordinateName = alias?.coordinate_display_name ?? displayName;
        const coordinate = coordinates.get(coordinateName);
        if (!coordinate) continue;
        seen.add(displayName);
        const rotationLabel = alias?.rotation_label ?? coordinate.label;
        highlights.push({
          category_type: "sector",
          category_label: "업종",
          display_name: displayName,
          public_category_id: `sector|${displayName}|${item.snapshot_date ?? "fallback"}`,
          rotation_label: rotationLabel,
          coordinate_display_name: coordinateName,
          mapping_basis: alias?.mapping_basis ?? "direct_coordinate",
          label: rotationLabel,
          x: coordinate.x,
          y: coordinate.y,
          radius: coordinate.radius,
          evidence_label: `리포트 ${item.report_count}건 / ${item.stock_count}종목`,
          evidence_source: "report_category_rollup",
          candidate_stocks: rotationCandidateStocks(database, businessDate, displayName),
          candidate_etfs: rotationCandidateEtfs(database, businessDate, etfMappings.get(`sector\0${displayName}`) ?? []),
        });
        if (highlights.length >= limit) break;
      }
      const payload: RotationOverlaySnapshot = {
        surface: "web-view",
        read_only: true,
        business_date: businessDate,
        image,
        highlights,
        notice: "업종·테마 위치 참고는 업종 기준 수동 좌표와 저장된 리포트 분류 요약을 겹쳐 본 설명용 화면입니다. 테마는 보조 근거이며 자금 순환을 계산하지 않고 확정 판단도 아닙니다.",
      };
      database.exec("COMMIT");
      return payload;
    } catch (error) {
      database.exec("ROLLBACK");
      throw error;
    }
  });
}
