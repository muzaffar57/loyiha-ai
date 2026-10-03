import { useEffect, useState } from "react";
import { AdminApiError, listAllAdminProducts, updateAdminStock } from "../lib/adminApi";
import { describeError, productTypeLabel, readyProducts, stockRequest } from "../lib/adminForms";
import type { AdminProduct } from "../types/admin";
import { AdminButton, Notice, TextField } from "./fields";

export function StockPage() {
  const [items, setItems] = useState<AdminProduct[]>([]);
  const [drafts, setDrafts] = useState<Record<number, string>>({});
  const [pending, setPending] = useState<{ id: number; next: number; current: number | null } | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    void listAllAdminProducts()
      .then((products) => {
        const ready = readyProducts(products);
        setItems(ready);
        setDrafts(Object.fromEntries(ready.map((item) => [item.id, String(item.available_quantity ?? 0)])));
      })
      .catch((reason: unknown) => setError(readError(reason)));
  }, []);

  return (
    <section className="grid gap-4">
      <div>
        <h2 className="text-2xl font-semibold">Tayyor mahsulotlar ombori</h2>
        <p className="mt-1 text-sm text-muted">Faqat tayyor mahsulotlar. Qoldiq serverdagi qiymat bilan yangilanadi.</p>
      </div>
      {message ? <Notice tone="ok">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      <ul className="grid gap-3">
        {items.map((item) => (
          <li key={item.id} className="min-w-0 rounded-3xl bg-white p-4">
            <p className="break-words font-semibold">{item.name}</p>
            <p className="text-sm text-muted">{productTypeLabel(item.product_type)} · SKU {item.sku ?? "—"}</p>
            <p className="mt-2 text-sm">Joriy qoldiq: {item.available_quantity ?? 0}</p>
            <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-end">
              <TextField
                label="Yangi qoldiq"
                type="number"
                min={0}
                value={drafts[item.id] ?? ""}
                onChange={(event) => setDrafts({ ...drafts, [item.id]: event.target.value })}
              />
              <AdminButton
                onClick={() => {
                  try {
                    const next = stockRequest(Number(drafts[item.id])).available_quantity;
                    setError("");
                    setPending({ id: item.id, next, current: item.available_quantity });
                  } catch (reason) {
                    setError(reason instanceof Error ? reason.message : "Qoldiq noto‘g‘ri.");
                  }
                }}
              >
                Saqlash
              </AdminButton>
            </div>
          </li>
        ))}
      </ul>
      {pending ? (
        <div className="fixed inset-0 z-40 flex items-end justify-center bg-ink/40 p-4 sm:items-center" role="dialog" aria-modal="true">
          <div className="w-full max-w-md rounded-3xl bg-white p-5">
            <h3 className="text-lg font-semibold">Qoldiqni tasdiqlang</h3>
            <p className="mt-2 text-sm">
              Joriy qoldiq {pending.current ?? 0}. Yangi qoldiq {pending.next}. Server tasdiqlaguncha bu qiymat saqlangan hisoblanmaydi.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <AdminButton
                onClick={() => {
                  const request = pending;
                  setPending(null);
                  void updateAdminStock(request.id, request.next)
                    .then((saved) => {
                      setItems((current) => current.map((item) => (item.id === saved.id ? saved : item)));
                      setDrafts((current) => ({ ...current, [saved.id]: String(saved.available_quantity ?? 0) }));
                      setMessage(`Qoldiq saqlandi: ${saved.available_quantity ?? 0}.`);
                      setError("");
                    })
                    .catch((reason: unknown) => setError(readError(reason)));
                }}
              >
                Tasdiqlash
              </AdminButton>
              <AdminButton tone="secondary" onClick={() => setPending(null)}>
                Bekor qilish
              </AdminButton>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function readError(reason: unknown): string {
  const status = reason instanceof AdminApiError ? reason.status : 0;
  const message = reason instanceof AdminApiError ? reason.message : "";
  return describeError(status, message);
}
