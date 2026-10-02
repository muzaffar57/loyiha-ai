import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CategoryArt } from "../components/CategoryArt";
import { EmptyState } from "../components/EmptyState";
import { Icon } from "../components/Icon";
import { PageHeader } from "../components/PageHeader";
import { SearchField } from "../components/SearchField";
import { listCategories, mediaUrl } from "../lib/storeApi";
import { useStoreResource } from "../lib/useStoreResource";
import type { StoreCategory } from "../types/store";

function matches(category: StoreCategory, query: string): boolean {
  const needle = query.trim().toLocaleLowerCase("uz");
  if (!needle) return true;
  const blob = [category.name, category.description ?? "", ...category.children.flatMap((child) => [child.name, child.description ?? ""])]
    .join(" ")
    .toLocaleLowerCase("uz");
  return blob.includes(needle);
}

function CatalogResults({ query, onRetry }: { query: string; onRetry: () => void }) {
  const state = useStoreResource("categories", () => listCategories());
  const results = useMemo(() => (state.status === "ready" ? state.data.items.filter((item) => matches(item, query)) : []), [state, query]);

  if (state.status === "loading") {
    return <div className="mt-4 h-28 animate-pulse rounded-3xl bg-mist" aria-busy="true" />;
  }
  if (state.status === "error") {
    return (
      <div className="mt-4">
        <EmptyState
          title="Katalog yuklanmadi"
          text={state.message}
          action={
            <button type="button" className="inline-flex min-h-12 items-center rounded-full bg-brand px-5 text-sm font-semibold text-white" onClick={onRetry}>
              Qayta urinish
            </button>
          }
        />
      </div>
    );
  }
  if (results.length === 0) {
    return (
      <div className="mt-4">
        <EmptyState title="Bo‘lim topilmadi" text="Boshqa so‘z bilan qidiring yoki butun katalogni oching." />
      </div>
    );
  }
  return (
    <>
      <p className="mt-3 text-sm text-muted">{results.length} ta bo‘lim. Mahsulot narxlari administrator kiritgach ochiladi.</p>
      <ul className="mt-4 grid gap-3 lg:grid-cols-2">
        {results.map((category) => (
          <li key={category.slug}>
            <Link to={`/katalog/${category.slug}`} className="flex min-h-[5.5rem] items-center gap-3 rounded-2xl border border-line bg-canvas p-2 pr-3">
              <span className="h-20 w-20 shrink-0 overflow-hidden rounded-xl">
                {mediaUrl(category.image) ? <img src={mediaUrl(category.image) ?? ""} alt="" className="h-full w-full object-cover" /> : <CategoryArt slug={category.slug} />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold leading-5">{category.name}</span>
                {category.description ? <span className="mt-1 block text-sm leading-5 text-muted">{category.description}</span> : null}
              </span>
              <Icon name="chevron" className="h-5 w-5 shrink-0 text-muted" />
            </Link>
          </li>
        ))}
      </ul>
    </>
  );
}

export function CatalogPage() {
  const [params, setParams] = useSearchParams();
  const initial = params.get("q") ?? "";
  const [query, setQuery] = useState(initial);
  const [attempt, setAttempt] = useState(0);

  function applySearch() {
    const trimmed = query.trim();
    if (trimmed) setParams({ q: trimmed });
    else setParams({});
  }

  return (
    <div className="lg:pt-8">
      <PageHeader title="Katalog" />
      <div className="mt-2">
        <SearchField
          id="catalog-search"
          value={query}
          onChange={setQuery}
          onSubmit={applySearch}
          label="Bo‘limlarni qidirish"
          placeholder="Bo‘lim yoki material"
        />
      </div>
      <CatalogResults key={attempt} query={query} onRetry={() => setAttempt((value) => value + 1)} />
      <p className="mt-6 text-sm leading-6 text-muted">
        Rustovka mahsulotlari keyinroq administrator orqali qo‘shiladi. Hozircha alohida bo‘lim ochilmagan.
      </p>
    </div>
  );
}
