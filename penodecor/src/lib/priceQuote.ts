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
