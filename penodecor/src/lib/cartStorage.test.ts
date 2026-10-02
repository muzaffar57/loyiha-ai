import assert from "node:assert/strict";
import test from "node:test";
import { parseCart } from "./cartStorage.ts";

test("bo‘sh yoki buzilgan savat bo‘sh ro‘yxat qaytaradi", () => {
  assert.deepEqual(parseCart(null), []);
  assert.deepEqual(parseCart("not-json"), []);
  assert.deepEqual(parseCart('{"id":"x"}'), []);
});

test("yaroqli qatorlarni saqlaydi va narxni o‘zi to‘ldirmaydi", () => {
  const raw = JSON.stringify([
    { id: "a", title: "Deraza romi", quantity: 2, detail: "En 120 sm", unitPriceLabel: "1 250 000 so‘m" },
    { id: "", title: "yo‘q", quantity: 1 },
    { id: "b", title: "Pilastr", quantity: 0 },
    { id: "c", title: "Baza", quantity: 1.5 },
  ]);
  assert.deepEqual(parseCart(raw), [
    {
      id: "a",
      title: "Deraza romi",
      quantity: 2,
      detail: "En 120 sm",
      unitPriceLabel: "1 250 000 so‘m",
    },
  ]);
});
