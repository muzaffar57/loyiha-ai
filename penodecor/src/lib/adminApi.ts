import type {
  AdminCategory,
  AdminProduct,
  AdminProductPage,
  AdminProfile,
  SyncResult,
  SyncStatus,
} from "../types/admin.ts";
import { clearAdminSessionNotice, clearAdminToken, getAdminToken, noteAdminSessionExpired, setAdminToken } from "./adminSession.ts";
import { imageDeleteBody, rejectPriceFields, stockRequest } from "./adminForms.ts";

export class AdminApiError extends Error {
  status: number;
  code: string | null;

  constructor(message: string, status: number, code: string | null = null) {
    super(message);
    this.name = "AdminApiError";
    this.status = status;
    this.code = code;
  }
}

function origin(): string {
  const env = import.meta.env as { VITE_STORE_API_URL?: string } | undefined;
  const configured = env?.VITE_STORE_API_URL ?? "http://localhost:8742";
  return configured.replace(/\/$/, "");
}

function messageFromBody(body: unknown): { message: string; code: string | null } {
  if (!body || typeof body !== "object") return { message: "", code: null };
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === "string") return { message: detail, code: null };
  if (Array.isArray(detail)) {
    const first = detail.find((item) => item && typeof item === "object" && typeof (item as { msg?: unknown }).msg === "string") as
      | { msg: string }
      | undefined;
    return { message: first?.msg ?? "", code: null };
  }
  if (detail && typeof detail === "object") {
    const record = detail as { message?: unknown; code?: unknown };
    return {
      message: typeof record.message === "string" ? record.message : "",
      code: typeof record.code === "string" ? record.code : null,
    };
  }
  return { message: "", code: null };
}

async function adminRequest<T>(path: string, init?: RequestInit, anonymous = false): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  if (!anonymous) {
    const token = getAdminToken();
    if (!token) throw new AdminApiError("Kirish talab qilinadi.", 401, null);
    headers.set("Authorization", `Bearer ${token}`);
  }
  let response: Response;
  try {
    response = await fetch(`${origin()}${path}`, { ...init, headers });
  } catch {
    throw new AdminApiError("Do‘kon serveriga ulanib bo‘lmadi.", 0, null);
  }
  if (!response.ok) {
    let parsed = { message: "", code: null as string | null };
    try {
      parsed = messageFromBody(await response.json());
    } catch {
      parsed = { message: "", code: null };
    }
    if (response.status === 401 && !anonymous) noteAdminSessionExpired();
    throw new AdminApiError(parsed.message, response.status, parsed.code);
  }
  return (await response.json()) as T;
}

function sendJson<T>(path: string, method: string, body: object): Promise<T> {
  const record = body as Record<string, unknown>;
  return adminRequest(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(record),
  });
}

export function adminLogin(email: string, password: string): Promise<void> {
  return adminRequest<{ access_token: string; token_type: string }>("/api/store/admin/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  }, true).then((body) => {
    setAdminToken(body.access_token);
  });
}

export function adminLogout(): void {
  clearAdminSessionNotice();
  clearAdminToken();
}

export function adminMe(): Promise<AdminProfile> {
  return adminRequest("/api/store/admin/me");
}

export function listAdminCategories(): Promise<{ items: AdminCategory[] }> {
  return adminRequest("/api/store/admin/categories");
}

export function createAdminCategory(body: Record<string, unknown>): Promise<AdminCategory> {
  rejectPriceFields(body);
  return sendJson("/api/store/admin/categories", "POST", body);
}

export function updateAdminCategory(id: number, body: Record<string, unknown>): Promise<AdminCategory> {
  rejectPriceFields(body);
  return sendJson(`/api/store/admin/categories/${id}`, "PATCH", body);
}

export function listAdminProducts(options: {
  categoryId?: number;
  q?: string;
  page?: number;
  pageSize?: number;
}): Promise<AdminProductPage> {
  const params = new URLSearchParams();
  if (options.categoryId) params.set("category_id", String(options.categoryId));
  if (options.q) params.set("q", options.q);
  if (options.page) params.set("page", String(options.page));
  if (options.pageSize) params.set("page_size", String(options.pageSize));
  const query = params.toString();
  return adminRequest(`/api/store/admin/products${query ? `?${query}` : ""}`);
}

export async function listAllAdminProducts(options: { categoryId?: number; q?: string } = {}): Promise<AdminProduct[]> {
  const pageSize = 100;
  const items: AdminProduct[] = [];
  let page = 1;
  let total = 0;
  do {
    const body = await listAdminProducts({ ...options, page, pageSize });
    total = body.total;
    items.push(...body.items);
    page += 1;
  } while (items.length < total && page <= 100);
  return items;
}

export function createAdminProduct(body: Record<string, unknown>): Promise<AdminProduct> {
  rejectPriceFields(body);
  return sendJson("/api/store/admin/products", "POST", body);
}

export function updateAdminProduct(id: number, body: Record<string, unknown>): Promise<AdminProduct> {
  rejectPriceFields(body);
  return sendJson(`/api/store/admin/products/${id}`, "PATCH", body);
}

export function updateAdminStock(id: number, quantity: number): Promise<AdminProduct> {
  return sendJson(`/api/store/admin/products/${id}/stock`, "PATCH", stockRequest(quantity));
}

export function uploadProductImage(id: number, file: File): Promise<AdminProduct> {
  const body = new FormData();
  body.set("file", file);
  return adminRequest(`/api/store/admin/products/${id}/images`, { method: "POST", body });
}

export function deleteProductImage(id: number, image: string): Promise<AdminProduct> {
  return sendJson(`/api/store/admin/products/${id}/images`, "DELETE", imageDeleteBody(image));
}

export function uploadCategoryImage(id: number, file: File): Promise<AdminCategory> {
  const body = new FormData();
  body.set("file", file);
  return adminRequest(`/api/store/admin/categories/${id}/image`, { method: "POST", body });
}

export function deleteCategoryImage(id: number, image: string): Promise<AdminCategory> {
  return sendJson(`/api/store/admin/categories/${id}/image`, "DELETE", imageDeleteBody(image));
}

export function adminSyncStatus(): Promise<SyncStatus> {
  return adminRequest("/api/store/admin/pricing/sync-status");
}

export function adminStartSync(): Promise<SyncResult> {
  return adminRequest("/api/store/admin/pricing/sync", { method: "POST" });
}
