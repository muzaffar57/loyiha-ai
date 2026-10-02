import { useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { CartContext, type CartContextValue } from "./cartContext";
import { readCart, writeCart } from "./cartStorage";

export function CartProvider({ children }: { children: ReactNode }) {
  const [lines, setLines] = useState(() => readCart());

  useEffect(() => {
    writeCart(lines);
  }, [lines]);

  const value = useMemo<CartContextValue>(
    () => ({
      lines,
      count: lines.reduce((sum, line) => sum + line.quantity, 0),
      removeLine: (id: string) => {
        setLines((current) => current.filter((line) => line.id !== id));
      },
    }),
    [lines],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}
