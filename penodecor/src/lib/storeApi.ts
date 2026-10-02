import type {
  PriceCalculateRequest,
  PriceQuoteResult,
  StoreCategory,
  StoreCategoryDetail,
  StoreProduct,
  StoreProductPage,
} from "../types/store";

export class StoreApiError extends Error {
  status: number;
  code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "StoreApiError";
    this.status = status;
    this.code = code;
  }
}

function origin(): string {
  const configured = import.meta.env.VITE_STORE_API_URL ?? "http://localhost:8742";
  return configured.replace(/\/$/, "");
}

export function mediaUrl(path: string | null | undefined): string | null {
  if (!path) return null;
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return `${origin()}${path.startsWith("/") ? path : `/${path}`}`;
}

function errorFromBody(body: unknown): { message: string; code: string | null } {
  const fallback = "So‘rov bajarilmadi.";
  if (!body || typeof body !== "object") return { message: fallback, code: null };
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) return { message: detail, code: null };
  if (detail && typeof detail === "object") {
    const record = detail as { message?: unknown; code?: unknown };
    const message = typeof record.message === "string" && record.message.trim() ? record.message : fallback;
    const code = typeof record.code === "string" ? record.code : null;
    return { message, code };
  }
  return { message: fallback, code: null };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${origin()}${path}`, init);
  } catch {
    throw new StoreApiError("Do‘kon serveriga ulanib bo‘lmadi.", 0);
  }
  if (!response.ok) {
    let parsed = { message: "So‘rov bajarilmadi.", code: null as string | null };
    try {
      parsed = errorFromBody(await response.json());
    } catch {
      parsed = { message: "So‘rov bajarilmadi.", code: null };
    }
    throw new StoreApiError(parsed.message, response.status, parsed.code);
  }
  return (await response.json()) as T;
}

export function listCategories(): Promise<{ items: StoreCategory[] }> {
  return request("/api/store/categories");
}

export function getCategory(slug: string): Promise<StoreCategoryDetail> {
  return request(`/api/store/categories/${encodeURIComponent(slug)}`);
}

export function listProducts(options: {
  category?: string;
  q?: string;
  page?: number;
  pageSize?: number;
  featured?: boolean;
  productType?: "made_to_order" | "ready_made";
}): Promise<StoreProductPage> {
  const params = new URLSearchParams();
  if (options.category) params.set("category", options.category);
  if (options.q) params.set("q", options.q);
  if (options.page) params.set("page", String(options.page));
  if (options.pageSize) params.set("page_size", String(options.pageSize));
  if (options.featured !== undefined) params.set("featured", String(options.featured));
  if (options.productType) params.set("product_type", options.productType);
  const query = params.toString();
  return request(`/api/store/products${query ? `?${query}` : ""}`);
}

export function getProduct(slug: string): Promise<StoreProduct> {
  return request(`/api/store/products/${encodeURIComponent(slug)}`);
}

export function calculatePrice(body: PriceCalculateRequest): Promise<PriceQuoteResult> {
  return request("/api/store/pricing/calculate", {
    method: "POST",
    headers: { Accept: "application/json", "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function listStock(options: { category?: string; q?: string; page?: number; pageSize?: number }): Promise<StoreProductPage> {
  const params = new URLSearchParams();
  if (options.category) params.set("category", options.category);
  if (options.q) params.set("q", options.q);
  if (options.page) params.set("page", String(options.page));
  if (options.pageSize) params.set("page_size", String(options.pageSize));
  const query = params.toString();
  return request(`/api/store/stock${query ? `?${query}` : ""}`);
}

const unitLabels: Record<StoreProduct["unit"], string> = {
  piece: "dona",
  meter: "metr",
  set: "komplekt",
};

export function unitLabel(unit: StoreProduct["unit"]): string {
  return unitLabels[unit];
}

export function formatStoredPrice(value: string): string {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  return `${new Intl.NumberFormat("uz-UZ").format(amount)} so‘m`;
}
