import { formatStoredPrice } from "../lib/storeApi";
import { adjustmentCaption, baseSellingPrice, displayTotal } from "../lib/priceQuote";
import type { PriceQuoteResult } from "../types/store";

export function PriceQuote({
  quote = null,
  manual = false,
  errorCode = null,
  errorMessage = null,
}: {
  quote?: PriceQuoteResult | null;
  manual?: boolean;
  errorCode?: string | null;
  errorMessage?: string | null;
}) {
  const manualState = manual || quote?.requires_manual_quote === true || quote?.status === "MANUAL_QUOTE_REQUIRED";
  const total = displayTotal(quote, manualState);

  if (manualState) {
    return (
      <section className="rounded-3xl border border-line bg-mist px-4 py-4" aria-live="polite">
        <h3 className="text-base font-semibold">Narx individual hisoblanadi</h3>
        <p className="mt-2 text-sm leading-6 text-muted">
          Shohona karniz uchun narx administrator taklifi bilan belgilanadi. Taxminiy summa ko‘rsatilmaydi.
        </p>
      </section>
    );
  }

  if (errorCode === "PRICE_NOT_CONFIGURED") {
    return (
      <section className="rounded-3xl border border-line bg-mist px-4 py-4">
        <h3 className="text-base font-semibold">Narx kiritilmagan</h3>
        <p className="mt-2 text-sm leading-6 text-muted">Bu mahsulot uchun narx hali sozlanmagan. Taxminiy narx ko‘rsatilmaydi.</p>
      </section>
    );
  }

  if (errorMessage) {
    return (
      <section className="rounded-3xl border border-line bg-mist px-4 py-4">
        <p className="text-sm leading-6">{errorMessage}</p>
      </section>
    );
  }

  if (!quote || total == null) return null;

  const base = baseSellingPrice(quote, manualState);
  const caption = adjustmentCaption(quote, manualState);

  return (
    <section className="rounded-3xl border border-line bg-canvas px-4 py-4" aria-live="polite">
      <h3 className="text-base font-semibold">Narx hisobi</h3>
      {quote.components.length > 0 ? (
        <ul className="mt-3 grid gap-2">
          {quote.components.map((component) => (
            <li key={component.code} className="flex items-start justify-between gap-3 text-sm">
              <span>
                <span className="font-semibold">{component.label}</span>
                {component.detail ? <span className="mt-1 block text-muted">{component.detail}</span> : null}
              </span>
              {component.amount ? <span className="shrink-0 font-semibold">{formatStoredPrice(component.amount)}</span> : null}
            </li>
          ))}
        </ul>
      ) : null}
      {base ? (
        <p className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-3 text-sm">
          <span className="text-muted">Asl narx</span>
          <span className="font-semibold">{formatStoredPrice(base)}</span>
        </p>
      ) : null}
      {caption ? <p className="mt-2 text-sm text-muted">Umumiy sozlama {caption}</p> : null}
      <p className="mt-4 flex items-center justify-between gap-3 border-t border-line pt-3 text-sm">
        <span className="text-muted">Jami</span>
        <span className="text-base font-semibold">{formatStoredPrice(total)}</span>
      </p>
      {quote.warnings.length > 0 ? (
        <ul className="mt-3 grid gap-1 text-sm text-muted">
          {quote.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
