import { useEffect, useState } from "react";
import { AdminApiError, adminStartSync, adminSyncStatus } from "../lib/adminApi";
import { describeError, syncStatusLabel } from "../lib/adminForms";
import type { SyncStatus } from "../types/admin";
import { AdminButton, Notice } from "./fields";

export function SyncPage() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  function load() {
    return adminSyncStatus().then(setStatus);
  }

  useEffect(() => {
    void load().catch((reason: unknown) => setError(readError(reason)));
  }, []);

  return (
    <section className="grid gap-4">
      <div>
        <h2 className="text-2xl font-semibold">Google Sheets sinxron holati</h2>
        <p className="mt-1 text-sm text-muted">Umumiy foiz va narxlar faqat o‘qish uchun. Kalitlar bu sahifada ko‘rinmaydi.</p>
      </div>
      {message ? <Notice tone="ok">{message}</Notice> : null}
      {error ? <Notice tone="error">{error}</Notice> : null}
      {status ? (
        <dl className="grid gap-3 rounded-3xl bg-white p-4 text-sm">
          <Row label="Holat" value={syncStatusLabel(status.status)} />
          <Row label="Eskirgan" value={status.stale ? "Ha" : "Yo‘q"} />
          <Row label="Valyuta" value={status.currency} />
          <Row label="Umumiy foiz" value={`${status.global_price_adjustment_percent}%`} />
          <Row label="Oxirgi muvaffaqiyat" value={formatServerTime(status.last_success_at)} />
          <Row label="Oxirgi urinish" value={formatServerTime(status.last_attempt_at)} />
          <Row label="Jadval vaqti" value={formatServerTime(status.sheet_updated_at)} />
          <Row label="Oxirgi xatolik" value={status.last_error ?? "Yo‘q"} />
        </dl>
      ) : null}
      <AdminButton
        disabled={pending}
        onClick={() => {
          setPending(true);
          setError("");
          void adminStartSync()
            .then((result) => {
              setMessage(`Sinxron tugadi. Yangilangan yozuvlar: ${result.updated_products}.`);
              return load();
            })
            .catch((reason: unknown) => setError(readError(reason)))
            .finally(() => setPending(false));
        }}
      >
        {pending ? "Sinxronlanmoqda..." : "Sinxronni boshlash"}
      </AdminButton>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <dt className="text-muted">{label}</dt>
      <dd className="break-words font-medium">{value}</dd>
    </div>
  );
}

function formatServerTime(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("uz-UZ", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function readError(reason: unknown): string {
  const status = reason instanceof AdminApiError ? reason.status : 0;
  const message = reason instanceof AdminApiError ? reason.message : "";
  return describeError(status, message);
}
