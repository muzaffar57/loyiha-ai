import { useEffect, useState } from "react";
import { AdminApiError, listAllAdminProducts } from "../lib/adminApi";
import { describeError, readOnlyPriceLabel, unpricedReadyProducts } from "../lib/adminForms";
import type { AdminProduct } from "../types/admin";
import { Notice } from "./fields";

export function UnpricedPage() {
  const [items, setItems] = useState<AdminProduct[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    void listAllAdminProducts()
      .then((products) => setItems(unpricedReadyProducts(products)))
      .catch((reason: unknown) => setError(readError(reason)));
  }, []);

  return (
    <section className="grid gap-4">
      <div>
        <h2 className="text-2xl font-semibold">Narxsiz mahsulotlar</h2>
        <p className="mt-1 text-sm text-muted">
          Tayyor mahsulotlarda sotuv narxi yo‘q. Narx Google Sheetsdan keladi va bu yerda tahrirlanmaydi.
        </p>
      </div>
      {error ? <Notice tone="error">{error}</Notice> : null}
      {items.length === 0 ? <p className="rounded-3xl bg-white p-4 text-sm">Narxsiz tayyor mahsulot yo‘q.</p> : null}
      <ul className="grid gap-3">
        {items.map((item) => (
          <li key={item.id} className="min-w-0 rounded-3xl bg-white p-4">
            <p className="break-words font-semibold">{item.name}</p>
            <p className="break-all text-sm text-muted">{item.slug}</p>
            <p className="mt-1 text-sm">SKU {item.sku ?? "—"} · {item.is_active ? "Faol" : "Nofaol"}</p>
            <p className="text-sm">Sotuv narxi: {readOnlyPriceLabel(item.selling_price)}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}

function readError(reason: unknown): string {
  const status = reason instanceof AdminApiError ? reason.status : 0;
  const message = reason instanceof AdminApiError ? reason.message : "";
  return describeError(status, message);
}
