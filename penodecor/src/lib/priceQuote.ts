import type { PriceQuoteResult } from "../types/store";

export function isManualQuoteCategory(slug: string): boolean {
  return slug === "shohona-karnizlar" || slug.startsWith("shohona-");
}

export function displayTotal(quote: PriceQuoteResult | null | undefined, manual = false): string | null {
  if (manual) return null;
  if (!quote || quote.requires_manual_quote || quote.status !== "PRICED") return null;
  if (quote.total == null || quote.total === "") return null;
  return quote.total;
}

export function baseSellingPrice(quote: PriceQuoteResult | null | undefined, manual = false): string | null {
  if (manual || !quote || quote.requires_manual_quote || quote.status !== "PRICED") return null;
  if (!quote.subtotal || !quote.total || quote.subtotal === quote.total) return null;
  return quote.subtotal;
}

export function adjustmentCaption(quote: PriceQuoteResult | null | undefined, manual = false): string | null {
  if (baseSellingPrice(quote, manual) == null) return null;
  const percent = quote?.applied?.global_price_adjustment_percent;
  if (!percent || percent === "0") return null;
  return percent.startsWith("-") ? `${percent}%` : `+${percent}%`;
}
