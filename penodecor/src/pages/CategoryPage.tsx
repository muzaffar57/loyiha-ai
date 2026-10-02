import { useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { CategoryArt } from "../components/CategoryArt";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { ProductCard } from "../components/ProductCard";
import { SearchField } from "../components/SearchField";
import { getCategory, listProducts, listStock, mediaUrl } from "../lib/storeApi";
import { useStoreResource } from "../lib/useStoreResource";

function CategoryBody({ slug, query }: { slug: string; query: string }) {
  const categoryState = useStoreResource(`category:${slug}`, () => getCategory(slug));
  const productState = useStoreResource(`products:${slug}:${query}`, () =>
    slug === "tayyor-mahsulotlar" ? listStock({ category: slug, q: query, pageSize: 12 }) : listProducts({ category: slug, q: query, pageSize: 12 }),
  );
  const [groupQuery, setGroupQuery] = useState("");

  const children = useMemo(() => {
    if (categoryState.status !== "ready") return [];
    const needle = groupQuery.trim().toLocaleLowerCase("uz");
    const items = categoryState.data.children;
    if (!needle) return items;
    return items.filter((child) => `${child.name} ${child.description ?? ""}`.toLocaleLowerCase("uz").includes(needle));
  }, [categoryState, groupQuery]);

  if (categoryState.status === "loading" || productState.status === "loading") {
    return <div className="mt-4 h-40 animate-pulse rounded-3xl bg-mist" aria-busy="true" />;
  }
  if (categoryState.status === "error") {
    return (
      <div className="mt-4">
        <EmptyState
          title={categoryState.statusCode === 404 ? "Bo‘lim topilmadi" : "Bo‘lim yuklanmadi"}
          text={categoryState.message}
          action={
            <Link to="/katalog" className="inline-flex min-h-12 items-center font-semibold text-brand">
              Katalogga qaytish
            </Link>
          }
        />
      </div>
    );
  }

  const category = categoryState.data;
  const readyMade = slug === "tayyor-mahsulotlar";
  const image = mediaUrl(category.image);

  return (
    <>
      <PageHeader title={category.name} back />
      <div className="mt-2 overflow-hidden rounded-3xl border border-line">
        <div className="h-36">{image ? <img src={image} alt="" className="h-full w-full object-cover" /> : <CategoryArt slug={category.slug} />}</div>
      </div>
      {category.parent ? (
        <p className="mt-3 text-sm text-muted">
          <Link to={`/katalog/${category.parent.slug}`} className="font-semibold text-brand">
            {category.parent.name}
          </Link>
        </p>
      ) : null}
      {category.description ? <p className="mt-3 text-sm leading-6 text-muted">{category.description}</p> : null}

      {category.children.length > 0 ? (
        <>
          <div className="mt-4">
            <SearchField id="group-search" value={groupQuery} onChange={setGroupQuery} label="Guruhlarni qidirish" placeholder="Guruh" />
          </div>
          <div className="mt-3 flex max-w-full gap-2 overflow-x-auto pb-1">
            <Link to={`/katalog/${category.slug}`} className="inline-flex min-h-11 shrink-0 items-center rounded-full bg-brand px-4 text-sm font-semibold text-white">
              Barchasi
            </Link>
            {children.map((child) => (
              <Link key={child.slug} to={`/katalog/${child.slug}`} className="inline-flex min-h-11 shrink-0 items-center rounded-full bg-mist px-4 text-sm font-semibold text-ink">
                {child.name}
              </Link>
            ))}
          </div>
        </>
      ) : null}

      {productState.status === "error" ? (
        <div className="mt-4">
          <EmptyState title="Mahsulotlar yuklanmadi" text={productState.message} />
        </div>
      ) : productState.data.items.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            title={readyMade ? "Tayyor mahsulot yo‘q" : "Mahsulot yo‘q"}
            text={
              readyMade
                ? "Ombordagi tayyor bezaklar shu yerda chiqadi. SKU, o‘lcham, narx va qoldiq administrator kiritadi."
                : "Bu bo‘limda hozircha mahsulot yo‘q. Narxlar administrator tomonidan kiritiladi."
            }
          />
        </div>
      ) : (
        <ul className="mt-4 grid grid-cols-2 gap-3 lg:grid-cols-3">
          {productState.data.items.map((product) => (
            <li key={product.slug}>
              <ProductCard product={product} />
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

export function CategoryPage() {
  const { slug = "" } = useParams();
  const [params, setParams] = useSearchParams();
  const applied = params.get("q") ?? "";
  const [draft, setDraft] = useState(applied);

  return (
    <div className="lg:pt-8">
      <div className="mb-3">
        <SearchField
          id="category-product-search"
          value={draft}
          onChange={setDraft}
          onSubmit={() => {
            const trimmed = draft.trim();
            if (trimmed) setParams({ q: trimmed });
            else setParams({});
          }}
          label="Mahsulot qidirish"
          placeholder="Mahsulot nomi"
        />
      </div>
      <CategoryBody key={`${slug}:${applied}`} slug={slug} query={applied} />
    </div>
  );
}
