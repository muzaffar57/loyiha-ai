import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { AdminApiError, adminMe, adminSyncStatus, listAdminCategories, listAllAdminProducts } from "../lib/adminApi";
import { describeError, syncStatusLabel, unpricedReadyProducts } from "../lib/adminForms";
import type { AdminCategory, AdminProduct, SyncStatus } from "../types/admin";
import { Notice } from "./fields";

export function DashboardPage() {
  const [name, setName] = useState("");
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [sync, setSync] = useState<SyncStatus | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    void Promise.all([adminMe(), listAdminCategories(), listAllAdminProducts(), adminSyncStatus()])
      .then(([profile, categoryPage, productItems, status]) => {
        setName(profile.full_name);
        setCategories(categoryPage.items);
        setProducts(productItems);
        setSync(status);
      })
      .catch((reason: unknown) => {
        const status = reason instanceof AdminApiError ? reason.status : 0;
        const message = reason instanceof AdminApiError ? reason.message : "";
        setError(describeError(status, message));
      });
  }, []);

  const activeProducts = products.filter((item) => item.is_active).length;
  const cards = [
    { label: "Kategoriyalar", value: String(categories.length), to: "/admin/kategoriyalar" },
    { label: "Mahsulotlar", value: String(products.length), to: "/admin/mahsulotlar" },
    { label: "Faol mahsulotlar", value: String(activeProducts), to: "/admin/mahsulotlar" },
    { label: "Tayyor ombor", value: String(products.filter((item) => item.product_type === "ready_made").length), to: "/admin/ombor" },
    { label: "Narxsiz tayyor", value: String(unpricedReadyProducts(products).length), to: "/admin/narxsiz" },
    { label: "Sinxron", value: sync ? syncStatusLabel(sync.status) : "—", to: "/admin/sinxron" },
  ];

  return (
    <section className="grid gap-4">
      <div>
        <h2 className="text-2xl font-semibold">Dashboard</h2>
        <p className="mt-1 text-sm text-muted">{name ? `${name}, boshqaruv paneli.` : "Yuklanmoqda..."}</p>
      </div>
      {error ? <Notice tone="error">{error}</Notice> : null}
      <div className="grid gap-3 sm:grid-cols-2">
        {cards.map((card) => (
          <Link key={card.label} to={card.to} className="min-w-0 rounded-3xl bg-white p-4">
            <p className="text-sm text-muted">{card.label}</p>
            <p className="mt-2 break-words text-2xl font-semibold text-brand">{card.value}</p>
          </Link>
        ))}
      </div>
      <p className="text-sm text-muted">Narx va umumiy foiz faqat o‘qiladi. Ular Google Sheets orqali yangilanadi.</p>
    </section>
  );
}
