import { useState, useSyncExternalStore } from "react";
import { Navigate } from "react-router-dom";
import { AdminButton, Notice, TextField } from "./fields";
import { AdminApiError, adminLogin } from "../lib/adminApi";
import { describeError } from "../lib/adminForms";
import { getAdminSessionNotice, getAdminToken, subscribeAdminSession } from "../lib/adminSession";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [entered, setEntered] = useState(false);
  const sessionNotice = useSyncExternalStore(subscribeAdminSession, getAdminSessionNotice, getAdminSessionNotice);

  if (getAdminToken() || entered) return <Navigate to="/admin" replace />;

  return (
    <div className="min-h-dvh overflow-x-hidden bg-mist px-4 py-10 text-ink">
      <form
        className="mx-auto w-full max-w-md min-w-0 rounded-3xl bg-white p-6 shadow-card"
        onSubmit={(event) => {
          event.preventDefault();
          setPending(true);
          setError("");
          void adminLogin(email, password)
            .then(() => setEntered(true))
            .catch((reason: unknown) => {
              const status = reason instanceof AdminApiError ? reason.status : 0;
              const message = reason instanceof AdminApiError ? reason.message : "";
              setError(describeError(status, message));
            })
            .finally(() => setPending(false));
        }}
      >
        <p className="text-xs uppercase tracking-[0.16em] text-brand">PenodecorPro</p>
        <h1 className="mt-2 text-2xl font-semibold">Do‘kon administratori</h1>
        <p className="mt-2 text-sm text-muted">Yuk tashish tizimidagi login bu yerda ishlatilmaydi.</p>
        <div className="mt-6 grid gap-4">
          <TextField label="Email" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <TextField
            label="Parol"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>
        {sessionNotice ? (
          <div className="mt-4">
            <Notice tone="error">{sessionNotice}</Notice>
          </div>
        ) : null}
        {error ? (
          <div className="mt-4">
            <Notice tone="error">{error}</Notice>
          </div>
        ) : null}
        <div className="mt-6">
          <AdminButton type="submit" disabled={pending}>
            {pending ? "Kirilmoqda..." : "Kirish"}
          </AdminButton>
        </div>
      </form>
    </div>
  );
}
