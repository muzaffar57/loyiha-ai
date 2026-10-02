import { useEffect, useRef, useState } from "react";
import { StoreApiError } from "./storeApi";

export type StoreLoad<T> =
  | { status: "loading" }
  | { status: "error"; message: string; statusCode?: number }
  | { status: "ready"; data: T };

export function useStoreResource<T>(key: string, load: () => Promise<T>): StoreLoad<T> {
  const loadRef = useRef(load);
  const [seenKey, setSeenKey] = useState(key);
  const [state, setState] = useState<StoreLoad<T>>({ status: "loading" });

  if (seenKey !== key) {
    setSeenKey(key);
    setState({ status: "loading" });
  }

  useEffect(() => {
    loadRef.current = load;
  });

  useEffect(() => {
    let cancelled = false;
    loadRef
      .current()
      .then((data) => {
        if (!cancelled) setState({ status: "ready", data });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        if (error instanceof StoreApiError) {
          setState({ status: "error", message: error.message, statusCode: error.status });
          return;
        }
        setState({ status: "error", message: "Do‘kon serveriga ulanib bo‘lmadi." });
      });
    return () => {
      cancelled = true;
    };
  }, [key]);

  return state;
}
