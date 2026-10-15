import { isBusinessDate } from "../../../domain/daily.ts";
import { getCategoryDetailSnapshot } from "../../../server/category-detail.ts";
import { cachedStoredJsonResponse } from "../../../server/stored-response-cache.ts";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

function methodNotAllowed(): Response {
  return new Response("method not allowed", {
    status: 405,
    headers: { allow: "GET", "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
  });
}

function invalidDate(): Response {
  return new Response("invalid date", {
    status: 400,
    headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
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
  const businessDate = query.get("date") ?? "";
  if (!isBusinessDate(businessDate)) return invalidDate();

  const requestedType = query.get("type")?.trim() ?? "";
  const categoryName = query.get("name")?.trim() ?? "";
  const requestedDisplayName = query.get("display_name")?.trim() ?? "";
  const publicCategory = parsedPublicCategory(query.get("public_category_id")?.trim() ?? "");
  if (publicCategory && requestedType && requestedType !== publicCategory.categoryType) return invalidCategory();
  const categoryType = publicCategory?.categoryType ?? requestedType;
  const categoryDisplayName = publicCategory?.displayName ?? requestedDisplayName;
  if (
    (categoryType !== "sector" && categoryType !== "theme") ||
    !(categoryDisplayName || categoryName) || categoryName.length > 120 || categoryDisplayName.length > 120
  ) {
    return invalidCategory();
  }

  try {
    return cachedStoredJsonResponse(request, [businessDate, categoryType, categoryName, categoryDisplayName || null], () => getCategoryDetailSnapshot(
      businessDate, categoryType, categoryName, categoryDisplayName || null,
    ));
  } catch {
    return new Response("category detail unavailable", {
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
