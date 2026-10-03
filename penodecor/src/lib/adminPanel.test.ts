import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { adminLogin, adminLogout, adminMe, createAdminProduct, updateAdminStock, uploadProductImage } from "./adminApi.ts";
import {
  categoryWriteBody,
  describeError,
  productCreateBody,
  productPatchBody,
  readOnlyPriceLabel,
  stockRequest,
  unpricedReadyProducts,
  type ProductFormInput,
} from "./adminForms.ts";
import {
  ADMIN_SESSION_EXPIRED,
  adminEntryPath,
  clearAdminSessionNotice,
  clearAdminToken,
  getAdminSessionNotice,
  getAdminToken,
  setAdminToken,
} from "./adminSession.ts";
import type { AdminProduct } from "../types/admin.ts";

const productInput: ProductFormInput = {
  name: "Rom",
  slug: "rom",
  description: "Tavsif",
  sku: "SKU-1",
  dimensions: "120 sm",
  categoryId: 3,
  sortOrder: 2,
  isActive: true,
  isFeatured: false,
  productType: "made_to_order",
  unit: "set",
};

test("token faqat xotirada turadi va logout uni tozalaydi", () => {
  const session = readFileSync(new URL("./adminSession.ts", import.meta.url), "utf8");
  const api = readFileSync(new URL("./adminApi.ts", import.meta.url), "utf8");
  const loginPage = readFileSync(new URL("../admin/LoginPage.tsx", import.meta.url), "utf8");
  const syncPage = readFileSync(new URL("../admin/SyncPage.tsx", import.meta.url), "utf8");
  for (const source of [session, api, loginPage, syncPage]) {
    assert.equal(source.includes("localStorage"), false);
    assert.equal(source.includes("sessionStorage"), false);
    assert.equal(source.includes("STORE_SHEETS"), false);
    assert.equal(source.includes("spreadsheet"), false);
    assert.equal(source.includes("private_key"), false);
  }
  assert.equal(loginPage.includes("getAdminSessionNotice"), true);
  assert.equal(session.includes(ADMIN_SESSION_EXPIRED), true);
  clearAdminSessionNotice();
  clearAdminToken();
  assert.equal(adminEntryPath(null), "/admin/login");
  setAdminToken("memory-token");
  assert.equal(getAdminToken(), "memory-token");
  assert.equal(getAdminSessionNotice(), null);
  assert.equal(adminEntryPath(getAdminToken()), "/admin");
  adminLogout();
  assert.equal(getAdminToken(), null);
  assert.equal(getAdminSessionNotice(), null);
  assert.equal(adminEntryPath(getAdminToken()), "/admin/login");
});

test("login do‘kon admin endpointiga yozadi va 401 sessiyani tozalaydi", async () => {
  clearAdminToken();
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  const original = globalThis.fetch;
  globalThis.fetch = (async (url: string | URL, init?: RequestInit) => {
    calls.push({ url: String(url), init });
    const path = String(url);
    if (path.endsWith("/api/store/admin/login")) {
      return new Response(JSON.stringify({ access_token: "store-token", token_type: "bearer" }), { status: 200 });
    }
    return new Response(JSON.stringify({ detail: "Kirish talab qilinadi." }), { status: 401 });
  }) as typeof fetch;
  try {
    await adminLogin("admin@penodecor.test", "secret-pass");
    assert.equal(getAdminToken(), "store-token");
    const login = calls[0];
    assert.equal(login?.url.endsWith("/api/store/admin/login"), true);
    assert.equal(login?.init?.body, JSON.stringify({ email: "admin@penodecor.test", password: "secret-pass" }));
    assert.equal(new Headers(login?.init?.headers).get("Authorization"), null);
    await assert.rejects(adminMe(), (error: { status?: number }) => error.status === 401);
    assert.equal(getAdminToken(), null);
    assert.equal(getAdminSessionNotice(), ADMIN_SESSION_EXPIRED);
    adminLogout();
    assert.equal(getAdminToken(), null);
    assert.equal(getAdminSessionNotice(), null);
  } finally {
    globalThis.fetch = original;
    clearAdminSessionNotice();
    clearAdminToken();
  }
});

test("kategoriya va mahsulot formasi narx maydonlarini yubormaydi", async () => {
  const category = categoryWriteBody({
    name: "Romlar",
    slug: "romlar",
    description: "Fasad",
    sortOrder: 4,
    isActive: false,
  });
  assert.deepEqual(category, {
    name: "Romlar",
    slug: "romlar",
    description: "Fasad",
    sort_order: 4,
    is_active: false,
  });
  const created = productCreateBody(productInput);
  assert.equal("selling_price" in created, false);
  assert.equal("images" in created, false);
  assert.equal("image" in category, false);
  assert.equal("available_quantity" in created, false);
  assert.equal("global_price_adjustment_percent" in created, false);
  assert.equal("pricing_rules" in created, false);
  assert.equal(created.product_type, "made_to_order");
  assert.equal(created.is_featured, false);
  const patched = productPatchBody({ ...productInput, sku: "NEW" }, "ready_made");
  assert.equal("sku" in patched, false);
  assert.equal("product_type" in patched, false);
  assert.equal(readOnlyPriceLabel(null), "Narx kiritilmagan");
  assert.equal(readOnlyPriceLabel("15000.00"), "15000.00");
  clearAdminToken();
  let called = false;
  const original = globalThis.fetch;
  globalThis.fetch = (async () => {
    called = true;
    return new Response("{}", { status: 500 });
  }) as typeof fetch;
  try {
    await assert.rejects(
      async () => {
        await createAdminProduct({ ...created, selling_price: "10" });
      },
      /Narx maydoni/,
    );
    assert.equal(called, false);
  } finally {
    globalThis.fetch = original;
  }
});

test("rasm yuklash va qoldiq yangilash server kontraktiga mos", async () => {
  clearAdminToken();
  setAdminToken("store-token");
  const calls: Array<{ url: string; method: string; body: unknown; type: string | null }> = [];
  const original = globalThis.fetch;
  globalThis.fetch = (async (url: string | URL, init?: RequestInit) => {
    const headers = new Headers(init?.headers);
    assert.equal(headers.get("Authorization"), "Bearer store-token");
    let body: unknown = init?.body;
    if (typeof body === "string") body = JSON.parse(body);
    if (body instanceof FormData) body = body.get("file");
    calls.push({ url: String(url), method: init?.method ?? "GET", body, type: headers.get("Content-Type") });
    return new Response(JSON.stringify({ id: 7, images: ["/media/store/products/7/a.jpg"], available_quantity: 5 }), { status: 200 });
  }) as typeof fetch;
  try {
    const file = new File([Uint8Array.from([1, 2, 3])], "rasm.jpg", { type: "image/jpeg" });
    await uploadProductImage(7, file);
    await updateAdminStock(7, 5);
    assert.equal(calls[0]?.url.endsWith("/api/store/admin/products/7/images"), true);
    assert.equal(calls[0]?.method, "POST");
    assert.equal(calls[0]?.type, null);
    assert.ok(calls[0]?.body instanceof File);
    assert.deepEqual(calls[1]?.body, { available_quantity: 5 });
    assert.equal(calls[1]?.url.endsWith("/api/store/admin/products/7/stock"), true);
    assert.throws(() => stockRequest(-1), /Qoldiq/);
    assert.deepEqual(stockRequest(0), { available_quantity: 0 });
  } finally {
    globalThis.fetch = original;
    clearAdminToken();
  }
});

test("himoyalangan yo‘l va server xabarlari", () => {
  assert.equal(describeError(401, ""), "Sessiya tugadi. Qayta kiring.");
  assert.equal(describeError(403, ""), "Bu amal uchun ruxsat yo‘q.");
  assert.equal(describeError(404, ""), "Ma’lumot topilmadi.");
  assert.equal(describeError(409, "Bu slug band."), "Bu slug band.");
  assert.equal(describeError(422, ""), "Ma’lumotlar noto‘g‘ri.");
  assert.equal(describeError(503, "Xizmat yo‘q."), "Xizmat yo‘q.");
  const priced = sampleProduct({ selling_price: "15000.00" });
  const missing = sampleProduct({ selling_price: null });
  assert.deepEqual(unpricedReadyProducts([priced, missing, { ...missing, id: 3, product_type: "made_to_order" }]).map((item) => item.id), [2]);
});

function sampleProduct(overrides: Partial<AdminProduct>): AdminProduct {
  return {
    id: 2,
    category_id: 1,
    name: "Blok",
    slug: "blok",
    description: null,
    sku: "TB-1",
    images: [],
    product_type: "ready_made",
    unit: "piece",
    dimensions: null,
    is_active: false,
    is_featured: false,
    sort_order: 0,
    selling_price: null,
    available_quantity: 0,
    ...overrides,
  };
}
