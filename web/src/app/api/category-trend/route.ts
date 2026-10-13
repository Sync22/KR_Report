import {
  getCategoryKeyTrendSnapshot,
  getCategoryTrendSnapshot,
  parseCategoryTrendLimit,
} from "../../../server/category-trend.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function invalidCategory(): Response {
  return new Response("invalid category", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function parsedPublicCategory(value: string): { categoryType: "sector" | "theme"; displayName: string } | undefined {
  const parts = value.split("|", 3);
  const categoryType = parts[0]?.trim();
  const displayName = parts[1]?.trim();
  return (categoryType === "sector" || categoryType === "theme") && displayName
    ? { categoryType, displayName }
    : undefined;
}

export function GET(request: Request): Response {
  const query = new URL(request.url).searchParams;
  const requestedType = query.get("type")?.trim() ?? "";
  const categoryName = query.get("name")?.trim() ?? "";
  const requestedDisplayName = query.get("display_name")?.trim() ?? "";
  const publicCategory = parsedPublicCategory(query.get("public_category_id")?.trim() ?? "");
  if (publicCategory && requestedType && requestedType !== publicCategory.categoryType) return invalidCategory();
  const categoryType = publicCategory?.categoryType ?? requestedType;
  const displayName = publicCategory?.displayName ?? (requestedDisplayName || categoryName);
  if (
    (categoryType !== "sector" && categoryType !== "theme") ||
    !displayName || displayName.length > 120 || categoryName.length > 120
  ) {
    return invalidCategory();
  }

  try {
    const limit = parseCategoryTrendLimit(query.get("limit"));
    const snapshot = publicCategory || requestedDisplayName
      ? getCategoryTrendSnapshot(categoryType, displayName, limit, categoryName)
      : getCategoryKeyTrendSnapshot(categoryType, categoryName, limit);
    return Response.json(snapshot, {
      headers: { "cache-control": "no-store" },
    });
  } catch {
    return new Response("category trend unavailable", {
      status: 503,
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }
}

export function HEAD(): Response { return methodNotAllowed(); }
export function OPTIONS(): Response { return methodNotAllowed(); }
export function POST(): Response { return methodNotAllowed(); }
export function PUT(): Response { return methodNotAllowed(); }
export function PATCH(): Response { return methodNotAllowed(); }
export function DELETE(): Response { return methodNotAllowed(); }
