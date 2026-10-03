import type { AdminProduct } from "../types/admin.ts";

const PRICE_KEYS = [
  "selling_price",
  "available_quantity",
  "global_price_adjustment_percent",
  "pricing_rules",
  "pricing_rule",
] as const;

export type CategoryFormInput = {
  name: string;
  slug: string;
  description: string;
  sortOrder: number;
  isActive: boolean;
};

export type ProductFormInput = {
  name: string;
  slug: string;
  description: string;
  sku: string;
  dimensions: string;
  categoryId: number;
  sortOrder: number;
  isActive: boolean;
  isFeatured: boolean;
  productType: "made_to_order" | "ready_made";
  unit: "piece" | "meter" | "set";
};

export function blankToNull(value: string): string | null {
  const text = value.trim();
  return text ? text : null;
}

export function rejectPriceFields(body: Record<string, unknown>): void {
  for (const key of PRICE_KEYS) {
    if (Object.prototype.hasOwnProperty.call(body, key)) {
      throw new Error("Narx maydoni yuborilmaydi.");
    }
  }
}

export function categoryWriteBody(input: CategoryFormInput): Record<string, unknown> {
  const body = {
    name: input.name.trim(),
    slug: input.slug.trim(),
    description: blankToNull(input.description),
    sort_order: input.sortOrder,
    is_active: input.isActive,
  };
  rejectPriceFields(body);
  return body;
}

export function productCreateBody(input: ProductFormInput): Record<string, unknown> {
  const body: Record<string, unknown> = {
    name: input.name.trim(),
    slug: input.slug.trim(),
    description: blankToNull(input.description),
    sku: blankToNull(input.sku),
    category_id: input.categoryId,
    dimensions: blankToNull(input.dimensions),
    product_type: input.productType,
    unit: input.unit,
    is_active: input.isActive,
    is_featured: input.isFeatured,
    sort_order: input.sortOrder,
  };
  rejectPriceFields(body);
  return body;
}

export function productPatchBody(input: ProductFormInput, productType: ProductFormInput["productType"]): Record<string, unknown> {
  const body: Record<string, unknown> = {
    name: input.name.trim(),
    slug: input.slug.trim(),
    description: blankToNull(input.description),
    category_id: input.categoryId,
    dimensions: blankToNull(input.dimensions),
    is_active: input.isActive,
    is_featured: input.isFeatured,
    sort_order: input.sortOrder,
  };
  if (productType !== "ready_made") {
    body.sku = blankToNull(input.sku);
  }
  rejectPriceFields(body);
  return body;
}

export function stockRequest(quantity: number): { available_quantity: number } {
  if (!Number.isInteger(quantity) || quantity < 0 || quantity > 1_000_000) {
    throw new Error("Qoldiq 0 dan 1000000 gacha butun son bo‘lishi kerak.");
  }
  return { available_quantity: quantity };
}

export function imageDeleteBody(image: string): { image: string } {
  return { image };
}

export function readyProducts(items: AdminProduct[]): AdminProduct[] {
  return items.filter((item) => item.product_type === "ready_made");
}

export function unpricedReadyProducts(items: AdminProduct[]): AdminProduct[] {
  return items.filter((item) => item.product_type === "ready_made" && item.selling_price === null);
}

export function readOnlyPriceLabel(value: string | null): string {
  return value ?? "Narx kiritilmagan";
}

export function productTypeLabel(value: AdminProduct["product_type"]): string {
  return value === "ready_made" ? "Tayyor mahsulot" : "Buyurtma asosida";
}

export function syncStatusLabel(status: string): string {
  if (status === "never") return "Hali sinxronlanmagan";
  if (status === "running") return "Sinxron ketmoqda";
  if (status === "ok") return "Muvaffaqiyatli";
  if (status === "error") return "Xato";
  return status;
}

export function fallbackStatusMessage(status: number): string {
  if (status === 401) return "Sessiya tugadi. Qayta kiring.";
  if (status === 403) return "Bu amal uchun ruxsat yo‘q.";
  if (status === 404) return "Ma’lumot topilmadi.";
  if (status === 409) return "Amal bajarilmadi. Server javobini tekshiring.";
  if (status === 413) return "Rasm hajmi ruxsat etilgan limitdan oshdi.";
  if (status === 422) return "Ma’lumotlar noto‘g‘ri.";
  if (status === 503) return "Xizmat vaqtincha ishlamayapti.";
  return "So‘rov bajarilmadi.";
}

export function describeError(status: number, serverMessage: string): string {
  const message = serverMessage.trim();
  return message || fallbackStatusMessage(status);
}
