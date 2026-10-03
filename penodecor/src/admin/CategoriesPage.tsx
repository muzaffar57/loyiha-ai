import { useEffect, useState } from "react";
import { mediaUrl } from "../lib/storeApi";
import {
  AdminApiError,
  createAdminCategory,
  deleteCategoryImage,
  listAdminCategories,
  updateAdminCategory,
  uploadCategoryImage,
} from "../lib/adminApi";
import { categoryWriteBody, describeError, type CategoryFormInput } from "../lib/adminForms";
import type { AdminCategory } from "../types/admin";
import { AdminButton, AreaField, CheckField, Notice, TextField } from "./fields";

const emptyForm: CategoryFormInput = { name: "", slug: "", description: "", sortOrder: 0, isActive: true };

export function CategoriesPage() {
  const [items, setItems] = useState<AdminCategory[]>([]);
  const [form, setForm] = useState<CategoryFormInput>(emptyForm);
  const [editing, setEditing] = useState<AdminCategory | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function reload() {
    return listAdminCategories().then((body) => setItems(body.items));
  }

  useEffect(() => {
    void reload().catch((reason: unknown) => setError(readError(reason)));
  }, []);

  function show(text: string) {
    setError("");
    setMessage(text);
  }

  return (
    <section className="grid gap-4">
      <h2 className="text-2xl font-semibold">Kategoriyalar</h2>
      {message ? <Notice tone="ok">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      <form
        className="grid gap-4 rounded-3xl bg-white p-4"
        onSubmit={(event) => {
          event.preventDefault();
          const body = categoryWriteBody(form);
          const action = editing ? updateAdminCategory(editing.id, body) : createAdminCategory(body);
          void action
            .then((saved) => {
              setEditing(saved);
              setForm(formFrom(saved));
              show(editing ? "Kategoriya yangilandi." : "Kategoriya yaratildi.");
              return reload();
            })
            .catch((reason: unknown) => setError(readError(reason)));
        }}
      >
        <h3 className="font-semibold">{editing ? "Kategoriyani tahrirlash" : "Yangi kategoriya"}</h3>
        <TextField label="Nom" value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} required />
        <TextField label="Slug" value={form.slug} onChange={(event) => setForm({ ...form, slug: event.target.value })} required />
        <AreaField label="Tavsif" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        <TextField
          label="Tartib"
          type="number"
          min={0}
          value={form.sortOrder}
          onChange={(event) => setForm({ ...form, sortOrder: Number(event.target.value) })}
        />
        <CheckField label="Faol" checked={form.isActive} onChange={(event) => setForm({ ...form, isActive: event.target.checked })} />
        <div className="flex flex-wrap gap-2">
          <AdminButton type="submit">{editing ? "Saqlash" : "Yaratish"}</AdminButton>
          {editing ? (
            <AdminButton
              tone="secondary"
              onClick={() => {
                setEditing(null);
                setForm(emptyForm);
              }}
            >
              Yangi forma
            </AdminButton>
          ) : null}
        </div>
        {editing ? (
          <CategoryImage
            category={editing}
            onChange={show}
            onError={setError}
            onSaved={(saved) => {
              setEditing(saved);
              setItems((current) => current.map((item) => (item.id === saved.id ? saved : item)));
            }}
          />
        ) : null}
      </form>
      <ul className="grid gap-3">
        {items.map((item) => (
          <li key={item.id} className="min-w-0 rounded-3xl bg-white p-4">
            <div className="flex min-w-0 flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="break-words font-semibold">{item.name}</p>
                <p className="break-all text-sm text-muted">{item.slug}</p>
                <p className="mt-1 text-sm">{item.is_active ? "Faol" : "Nofaol"} · tartib {item.sort_order}</p>
              </div>
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

function CategoryImage({
  category,
  onChange,
  onError,
  onSaved,
}: {
  category: AdminCategory;
  onChange: (message: string) => void;
  onError: (message: string) => void;
  onSaved: (category: AdminCategory) => void;
}) {
  const preview = mediaUrl(category.image);
  return (
    <div className="grid gap-3 border-t border-line pt-4">
      <p className="text-sm font-medium">Rasm</p>
      {preview ? <img src={preview} alt="" className="h-36 w-full rounded-2xl object-cover" /> : <p className="text-sm text-muted">Rasm yo‘q</p>}
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp"
        className="w-full min-w-0 text-sm"
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = "";
          if (!file) return;
          void uploadCategoryImage(category.id, file)
            .then((saved) => {
              onSaved(saved);
              onChange("Kategoriya rasmi yuklandi.");
            })
            .catch((reason: unknown) => onError(readError(reason)));
        }}
      />
      {category.image ? (
        <AdminButton
          tone="danger"
          onClick={() => {
            const image = category.image;
            if (!image) return;
            void deleteCategoryImage(category.id, image)
              .then((saved) => {
                onSaved(saved);
                onChange("Kategoriya rasmi o‘chirildi.");
              })
              .catch((reason: unknown) => onError(readError(reason)));
          }}
        >
          Rasmni o‘chirish
        </AdminButton>
      ) : null}
    </div>
  );
}

function formFrom(category: AdminCategory): CategoryFormInput {
  return {
    name: category.name,
    slug: category.slug,
    description: category.description ?? "",
    sortOrder: category.sort_order,
    isActive: category.is_active,
  };
}

function readError(reason: unknown): string {
  const status = reason instanceof AdminApiError ? reason.status : 0;
  const message = reason instanceof AdminApiError ? reason.message : "";
  return describeError(status, message);
}
