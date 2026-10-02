export type CartLine = {
  id: string;
  title: string;
  quantity: number;
  detail?: string;
  unitPriceLabel?: string;
};

const STORAGE_KEY = "penodecor.cart.v1";
const MAX_TITLE = 160;
const MAX_DETAIL = 240;
const MAX_PRICE_LABEL = 40;
const MAX_LINES = 50;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalText(value: unknown, max: number): string | undefined {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  if (!trimmed) return undefined;
  return trimmed.slice(0, max);
}

export function parseCart(raw: string | null): CartLine[] {
  if (!raw) return [];
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return [];
  }
  if (!Array.isArray(parsed)) return [];

  const lines: CartLine[] = [];
  for (const item of parsed) {
    if (lines.length >= MAX_LINES || !isRecord(item)) continue;
    const id = optionalText(item.id, 80);
    const title = optionalText(item.title, MAX_TITLE);
    const quantity = item.quantity;
    if (!id || !title || typeof quantity !== "number" || !Number.isInteger(quantity)) continue;
    if (quantity < 1 || quantity > 999) continue;
    const line: CartLine = { id, title, quantity };
    const detail = optionalText(item.detail, MAX_DETAIL);
    const unitPriceLabel = optionalText(item.unitPriceLabel, MAX_PRICE_LABEL);
    if (detail) line.detail = detail;
    if (unitPriceLabel) line.unitPriceLabel = unitPriceLabel;
    lines.push(line);
  }
  return lines;
}

export function readCart(): CartLine[] {
  try {
    return parseCart(localStorage.getItem(STORAGE_KEY));
  } catch {
    return [];
  }
}

export function writeCart(lines: CartLine[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(lines));
  } catch {
    // Xotiraga yozib bo‘lmasa savat joriy sahifada qoladi.
  }
}
