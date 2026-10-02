import assert from "node:assert/strict";
import test from "node:test";
import { displayTotal, isManualQuoteCategory } from "./priceQuote.ts";
import type { PriceQuoteResult } from "../types/store.ts";

function quote(overrides: Partial<PriceQuoteResult> = {}): PriceQuoteResult {
  return {
    status: "PRICED",
    currency: "UZS",
    unit_price: "24000.00",
    subtotal: "48000.00",
    total: "48000.00",
    components: [],
    requires_manual_quote: false,
    warnings: [],
    applied: {},
    ...overrides,
  };
}

test("shohona toifasida narx individual hisoblanadi", () => {
  assert.equal(isManualQuoteCategory("shohona-karnizlar"), true);
  assert.equal(isManualQuoteCategory("shohona-katta"), true);
  assert.equal(isManualQuoteCategory("shift-karnizlari"), false);
});

test("qo‘lda narx va bo‘sh konfiguratsiya summa ko‘rsatmaydi", () => {
  assert.equal(displayTotal(quote({ status: "MANUAL_QUOTE_REQUIRED", total: "0", requires_manual_quote: true })), null);
  assert.equal(displayTotal(quote(), true), null);
  assert.equal(displayTotal(quote({ total: null })), null);
  assert.equal(displayTotal(null), null);
});

test("server qaytargan summa o‘zgartirilmaydi", () => {
  assert.equal(displayTotal(quote()), "48000.00");
});
