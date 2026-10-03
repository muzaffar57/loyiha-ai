export const ADMIN_SESSION_EXPIRED = "Sessiya muddati tugadi. Iltimos, qayta kiring.";

let token: string | null = null;
let sessionNotice: string | null = null;
const listeners = new Set<() => void>();

function emit(): void {
  for (const listener of listeners) listener();
}

export function getAdminToken(): string | null {
  return token;
}

export function getAdminSessionNotice(): string | null {
  return sessionNotice;
}

export function setAdminToken(value: string): void {
  token = value;
  sessionNotice = null;
  emit();
}

export function clearAdminToken(): void {
  token = null;
  emit();
}

export function noteAdminSessionExpired(): void {
  sessionNotice = ADMIN_SESSION_EXPIRED;
  token = null;
  emit();
}

export function clearAdminSessionNotice(): void {
  if (sessionNotice === null) return;
  sessionNotice = null;
  emit();
}

export function subscribeAdminSession(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function isAdminAuthenticated(): boolean {
  return token !== null;
}

export function adminEntryPath(currentToken: string | null): "/admin" | "/admin/login" {
  return currentToken ? "/admin" : "/admin/login";
}
