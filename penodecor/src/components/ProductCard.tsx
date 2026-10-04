import { Link } from "react-router-dom";
import { formatStoredPrice, mediaUrl, unitLabel } from "../lib/storeApi";
import type { StoreProduct } from "../types/store";
import { CategoryArt } from "./CategoryArt";

export function ProductCard({ product }: { product: StoreProduct }) {
  const image = mediaUrl(product.images[0]);
  return (
    <Link to={`/mahsulot/${product.slug}`} className="block overflow-hidden rounded-2xl border border-line bg-canvas">
      <div className="aspect-[4/3] overflow-hidden bg-mist">
        {image ? (
          <img src={image} alt="" className="h-full w-full object-contain" />
        ) : (
          <CategoryArt slug={product.category.slug} />
        )}
      </div>
      <div className="p-3">
        <p className="text-sm font-semibold leading-5">{product.name}</p>
        {product.dimensions ? <p className="mt-1 text-xs text-muted">{product.dimensions}</p> : null}
        {product.product_type === "ready_made" && product.selling_price ? (
          <p className="mt-2 text-sm font-semibold text-brand">{formatStoredPrice(product.selling_price)}</p>
        ) : (
          <p className="mt-2 text-xs leading-5 text-muted">Narx administrator kiritadi.</p>
        )}
        <p className="mt-1 text-xs text-muted">
          {unitLabel(product.unit)}
          {product.sku ? ` · ${product.sku}` : ""}
          {product.available_quantity !== null ? ` · omborda ${product.available_quantity}` : ""}
        </p>
      </div>
    </Link>
  );
}
