import { useState, type FormEvent } from "react";
import { PriceQuote } from "./PriceQuote";
import { StoreApiError, calculatePrice } from "../lib/storeApi";
import type { PriceQuoteResult } from "../types/store";

export function CorniceQuote({ productId }: { productId: number }) {
  const [size, setSize] = useState("20");
  const [length, setLength] = useState("1");
  const [coating, setCoating] = useState(false);
  const [quote, setQuote] = useState<PriceQuoteResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const width = size.replace(",", ".").trim();
    const meters = length.replace(",", ".").trim();
    const widthNumber = Number(width);
    const lengthNumber = Number(meters);
    if (!Number.isFinite(widthNumber) || widthNumber < 15) {
      setQuote(null);
      setErrorCode(null);
      setError("Razmer kamida 15 sm bo‘lishi kerak.");
      return;
    }
    if (!Number.isFinite(lengthNumber) || lengthNumber <= 0) {
      setQuote(null);
      setErrorCode(null);
      setError("Uzunlikni metrda yozing.");
      return;
    }
    setPending(true);
    setError(null);
    setErrorCode(null);
    try {
      const result = await calculatePrice({
        product_id: productId,
        quantity: 1,
        cornice: { width_cm: width, length_m: meters, coating },
      });
      setQuote(result);
    } catch (caught) {
      setQuote(null);
      if (caught instanceof StoreApiError) {
        setError(caught.message);
        setErrorCode(caught.code);
      } else {
        setError("Narx hisoblanmadi.");
        setErrorCode(null);
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <form className="mt-4 rounded-3xl border border-line bg-white p-4" onSubmit={onSubmit}>
      <h3 className="text-base font-semibold">Razmer bo‘yicha narx</h3>
      <p className="mt-2 text-sm leading-6 text-muted">Har karnizning o‘z eni bor. 20 sm gacha proporsional hisoblanadi. 20–25 sm da qalinlikka 1 sm, 25 sm dan keyin 2 sm qo‘shiladi. Eng kichik razmer 15 sm.</p>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm font-semibold">
          Razmer, sm
          <input
            inputMode="decimal"
            value={size}
            onChange={(event) => setSize(event.target.value)}
            className="min-h-12 rounded-2xl border border-line bg-mist px-4 text-base font-normal"
          />
        </label>
        <label className="grid gap-1 text-sm font-semibold">
          Uzunlik, metr
          <input
            inputMode="decimal"
            value={length}
            onChange={(event) => setLength(event.target.value)}
            className="min-h-12 rounded-2xl border border-line bg-mist px-4 text-base font-normal"
          />
        </label>
      </div>
      <label className="mt-3 flex min-h-12 items-center gap-3 text-sm font-semibold">
        <input type="checkbox" checked={coating} onChange={(event) => setCoating(event.target.checked)} className="h-5 w-5 accent-accent" />
        Qoplama bor
      </label>
      <button type="submit" disabled={pending} className="mt-3 inline-flex min-h-12 items-center rounded-full bg-accent px-5 text-sm font-semibold text-white disabled:opacity-60">
        {pending ? "Hisoblanmoqda..." : "Hisoblash"}
      </button>
      {quote || error ? (
        <div className="mt-4">
          <PriceQuote quote={quote} errorCode={errorCode} errorMessage={quote ? null : error} />
        </div>
      ) : null}
    </form>
  );
}
