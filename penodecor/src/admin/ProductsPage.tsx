import { useEffect, useState } from "react";
import { mediaUrl } from "../lib/storeApi";
import {
  AdminApiError,
  createAdminProduct,
  deleteProductImage,
  listAdminCategories,
  listAllAdminProducts,
  updateAdminProduct,
  uploadProductImage,
} from "../lib/adminApi";
import { describeError, productCreateBody, productPatchBody, productTypeLabel, readOnlyPriceLabel, type ProductFormInput } from "../lib/adminForms";
import type { AdminCategory, AdminProduct } from "../types/admin";
import { AdminButton, AreaField, CheckField, Notice, SelectField, TextField } from "./fields";

const emptyForm: ProductFormInput = {
  name: "",
  slug: "",
  description: "",
  sku: "",
  dimensions: "",
  categoryId: 0,
  sortOrder: 0,
  isActive: true,
  isFeatured: false,
  productType: "made_to_order",
  unit: "piece",
};

export function ProductsPage() {
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [items, setItems] = useState<AdminProduct[]>([]);
  const [query, setQuery] = useState("");
  const [categoryId, setCategoryId] = useState(0);
  const [form, setForm] = useState<ProductFormInput>(emptyForm);
  const [editing, setEditing] = useState<AdminProduct | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function reload(nextQuery = query, nextCategory = categoryId) {
    return listAllAdminProducts({
      q: nextQuery.trim() || undefined,
      categoryId: nextCategory || undefined,
    }).then(setItems);
  }

  useEffect(() => {
    void Promise.all([listAdminCategories(), listAllAdminProducts()])
      .then(([categoryPage, products]) => {
        setCategories(categoryPage.items);
        setItems(products);
        setForm((current) => ({ ...current, categoryId: current.categoryId || categoryPage.items[0]?.id || 0 }));
      })
      .catch((reason: unknown) => setError(readError(reason)));
  }, []);

  return (
    <section className="grid gap-4">
      <h2 className="text-2xl font-semibold">Mahsulotlar</h2>
      {message ? <Notice tone="ok">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      <form
        className="grid gap-3 rounded-3xl bg-white p-4 sm:grid-cols-[1fr_1fr_auto]"
        onSubmit={(event) => {
          event.preventDefault();
          void reload().catch((reason: unknown) => setError(readError(reason)));
        }}
      >
        <TextField label="Qidiruv" value={query} onChange={(event) => setQuery(event.target.value)} />
        <SelectField label="Kategoriya" value={categoryId} onChange={(event) => setCategoryId(Number(event.target.value))}>
          <option value={0}>Barchasi</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
              {category.is_active ? "" : " (nofaol)"}
            </option>
          ))}
        </SelectField>
        <div className="self-end">
          <AdminButton type="submit">Filtrlash</AdminButton>
        </div>
      </form>
      <form
        className="grid gap-4 rounded-3xl bg-white p-4"
        onSubmit={(event) => {
          event.preventDefault();
          const action = editing
            ? updateAdminProduct(editing.id, productPatchBody(form, editing.product_type))
            : createAdminProduct(productCreateBody({ ...form, categoryId: form.categoryId || categories[0]?.id || 0 }));
          void action
            .then((saved) => {
              setEditing(saved);
              setForm(formFrom(saved));
              setMessage(editing ? "Mahsulot yangilandi." : "Mahsulot yaratildi.");
              setError("");
              return reload();
            })
            .catch((reason: unknown) => setError(readError(reason)));
        }}
      >
        <h3 className="font-semibold">{editing ? "Mahsulotni tahrirlash" : "Yangi mahsulot"}</h3>
        <TextField label="Nom" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
        <TextField label="Slug" value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} required />
        <AreaField label="Tavsif" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        <TextField
          label="SKU"
          value={form.sku}
          disabled={editing?.product_type === "ready_made"}
          onChange={(event) => setForm({ ...form, sku: event.target.value })}
        />
        <TextField label="O‘lchamlar" value={form.dimensions} onChange={(event) => setForm({ ...form, dimensions: event.target.value })} />
        <SelectField label="Kategoriya" value={form.categoryId} onChange={(event) => setForm({ ...form, categoryId: Number(event.target.value) })}>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>
              {category.name}
            </option>
          ))}
        </SelectField>
        {editing ? (
          <p className="text-sm text-muted">
            {productTypeLabel(editing.product_type)} · {unitLabel(editing.unit)} · Narx: {readOnlyPriceLabel(editing.selling_price)}
          </p>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2">
            <SelectField
              label="Turi"
              value={form.productType}
              onChange={(event) => {
                const productType = event.target.value as ProductFormInput["productType"];
                setForm({ ...form, productType, isActive: productType === "ready_made" ? false : form.isActive });
              }}
            >
              <option value="made_to_order">Buyurtma asosida</option>
              <option value="ready_made">Tayyor mahsulot</option>
            </SelectField>
            <SelectField label="O‘lchov" value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value as ProductFormInput["unit"] })}>
              <option value="piece">dona</option>
              <option value="meter">metr</option>
              <option value="set">komplekt</option>
            </SelectField>
          </div>
        )}
        <TextField
          label="Tartib"
          type="number"
          min={0}
          value={form.sortOrder}
          onChange={(event) => setForm({ ...form, sortOrder: Number(event.target.value) })}
        />
        <CheckField label="Faol" checked={form.isActive} onChange={(event) => setForm({ ...form, isActive: event.target.checked })} />
        <CheckField label="Tanlangan" checked={form.isFeatured} onChange={(event) => setForm({ ...form, isFeatured: event.target.checked })} />
        <div className="flex flex-wrap gap-2">
          <AdminButton type="submit">{editing ? "Saqlash" : "Yaratish"}</AdminButton>
          {editing ? (
            <AdminButton
              tone="secondary"
              onClick={() => {
                setEditing(null);
                setForm({ ...emptyForm, categoryId: categories[0]?.id ?? 0 });
              }}
            >
              Yangi forma
            </AdminButton>
          ) : null}
        </div>
        {editing ? (
          <ProductImages
            product={editing}
            onSaved={(saved) => {
              setEditing(saved);
              setItems((current) => current.map((item) => (item.id === saved.id ? saved : item)));
            }}
            onMessage={(text) => {
              setError("");
              setMessage(text);
            }}
            onError={setError}
          />
        ) : null}
      </form>
      <ul className="grid gap-3">
        {items.map((item) => (
          <li key={item.id} className="min-w-0 rounded-3xl bg-white p-4">
            <p className="break-words font-semibold">{item.name}</p>
            <p className="break-all text-sm text-muted">{item.slug}</p>
            <p className="mt-1 text-sm">
              {productTypeLabel(item.product_type)} · {item.is_active ? "Faol" : "Nofaol"}
              {item.is_featured ? " · Tanlangan" : ""}
            </p>
            <p className="text-sm">Narx: {readOnlyPriceLabel(item.selling_price)}</p>
            <div className="mt-3">
              <AdminButton
                tone="secondary"
                onClick={() => {
                  setEditing(item);
                  setForm(formFrom(item));
                }}
              >
                Tahrirlash
              </AdminButton>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function ProductImages({
  product,
  onSaved,
  onMessage,
  onError,
}: {
  product: AdminProduct;
  onSaved: (product: AdminProduct) => void;
  onMessage: (message: string) => void;
  onError: (message: string) => void;
}) {
  return (
    <div className="grid gap-3 border-t border-line pt-4">
      <p className="text-sm font-medium">Rasmlar ({product.images.length}/8)</p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        {product.images.map((image) => {
          const src = mediaUrl(image);
          return (
            <figure key={image} className="min-w-0">
              {src ? <img src={src} alt="" className="h-28 w-full rounded-2xl bg-mist object-contain" /> : null}
              <AdminButton
                tone="danger"
                onClick={() => {
                  void deleteProductImage(product.id, image)
                    .then((saved) => {
                      onSaved(saved);
                      onMessage("Rasm o‘chirildi.");
                    })
                    .catch((reason: unknown) => onError(readError(reason)));
                }}
              >
                O‘chirish
              </AdminButton>
            </figure>
          );
        })}
      </div>
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="w-full min-w-0 text-sm"
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          void uploadProductImage(product.id, file)
            .then((saved) => {
              onSaved(saved);
              onMessage("Rasm yuklandi.");
            })
            .catch((reason: unknown) => onError(readError(reason)));
        }}
      />
    </div>
  );
}

function formFrom(product: AdminProduct): ProductFormInput {
  return {
    name: product.name,
    slug: product.slug,
    description: product.description ?? "",
    sku: product.sku ?? "",
    dimensions: product.dimensions ?? "",
    categoryId: product.category_id,
    sortOrder: product.sort_order,
    isActive: product.is_active,
    isFeatured: product.is_featured,
    productType: product.product_type,
    unit: product.unit,
  };
}

function unitLabel(unit: AdminProduct["unit"]): string {
  if (unit === "meter") return "metr";
  if (unit === "set") return "komplekt";
  return "dona";
}

function readError(reason: unknown): string {
  const status = reason instanceof AdminApiError ? reason.status : 0;
  const message = reason instanceof AdminApiError ? reason.message : "";
  return describeError(status, message);
}
