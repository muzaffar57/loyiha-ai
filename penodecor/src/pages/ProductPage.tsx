import { Link, useParams } from "react-router-dom";
import { CategoryArt } from "../components/CategoryArt";
import { EmptyState } from "../components/EmptyState";
import { PageHeader } from "../components/PageHeader";
import { PriceQuote } from "../components/PriceQuote";
import { isManualQuoteCategory } from "../lib/priceQuote";
import { formatStoredPrice, getProduct, mediaUrl, unitLabel } from "../lib/storeApi";
import { useStoreResource } from "../lib/useStoreResource";

export function ProductPage() {
  const { slug = "" } = useParams();
  const state = useStoreResource(`product:${slug}`, () => getProduct(slug));
  const product = state.status === "ready" ? state.data : null;

  return (
    <div className="lg:pt-8">
      <PageHeader title={product?.name ?? "Mahsulot"} back />
      {state.status === "loading" ? <div className="mt-4 h-40 animate-pulse rounded-3xl bg-mist" aria-busy="true" /> : null}
      {state.status === "error" ? (
        <div className="mt-4">
          <EmptyState
            title={state.statusCode === 404 ? "Mahsulot topilmadi" : "Mahsulot yuklanmadi"}
            text={state.statusCode === 404 ? "Bu mahsulot yo‘q yoki yashirilgan. Narx administrator kiritgan kartochkadan olinadi." : state.message}
            action={
              <Link to="/katalog" className="inline-flex min-h-12 items-center font-semibold text-brand">
                Katalogga qaytish
              </Link>
            }
          />
        </div>
      ) : null}
      {product ? (
        <article className="mt-4">
          <div className="overflow-hidden rounded-3xl border border-line bg-mist">
            {product.images.length > 0 ? (
              <img src={mediaUrl(product.images[0]) ?? ""} alt={product.name} className="mx-auto max-h-[70vh] w-full object-contain" />
            ) : (
              <div className="h-48">
                <CategoryArt slug={product.category.slug} />
              </div>
            )}
          </div>
          <p className="mt-4 text-sm text-muted">
            <Link to={`/katalog/${product.category.slug}`} className="font-semibold text-brand">
              {product.category.name}
            </Link>
          </p>
          <h2 className="mt-2 text-2xl font-semibold">{product.name}</h2>
          {product.description ? <p className="mt-3 text-sm leading-6">{product.description}</p> : null}
          <dl className="mt-4 grid gap-2 text-sm">
            <div className="flex justify-between gap-3 rounded-2xl bg-mist px-4 py-3">
              <dt className="text-muted">Turi</dt>
              <dd className="font-semibold">{product.product_type === "ready_made" ? "Tayyor" : "Buyurtma asosida"}</dd>
            </div>
            <div className="flex justify-between gap-3 rounded-2xl bg-mist px-4 py-3">
              <dt className="text-muted">O‘lchov</dt>
              <dd className="font-semibold">{unitLabel(product.unit)}</dd>
            </div>
            {product.sku ? (
              <div className="flex justify-between gap-3 rounded-2xl bg-mist px-4 py-3">
                <dt className="text-muted">Kod</dt>
                <dd className="font-semibold">{product.sku}</dd>
              </div>
            ) : null}
            {product.dimensions ? (
              <div className="flex justify-between gap-3 rounded-2xl bg-mist px-4 py-3">
                <dt className="text-muted">O‘lcham</dt>
                <dd className="text-right font-semibold">{product.dimensions}</dd>
              </div>
            ) : null}
            {product.product_type === "ready_made" && product.available_quantity !== null ? (
              <div className="flex justify-between gap-3 rounded-2xl bg-mist px-4 py-3">
                <dt className="text-muted">Omborda</dt>
                <dd className="font-semibold">{product.available_quantity}</dd>
              </div>
            ) : null}
            {isManualQuoteCategory(product.category.slug) ? null : (
              <div className="flex justify-between gap-3 rounded-2xl bg-mist px-4 py-3">
                <dt className="text-muted">Narx</dt>
                <dd className="text-right font-semibold">
                  {product.product_type === "ready_made" && product.selling_price ? formatStoredPrice(product.selling_price) : "Administrator kiritadi"}
                </dd>
              </div>
            )}
          </dl>
          {isManualQuoteCategory(product.category.slug) ? (
            <div className="mt-4">
              <PriceQuote manual />
            </div>
          ) : null}
        </article>
      ) : null}
    </div>
  );
}
