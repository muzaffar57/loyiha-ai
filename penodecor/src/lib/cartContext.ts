import { createContext } from "react";
import type { CartLine } from "./cartStorage";

export type CartContextValue = {
  lines: CartLine[];
  count: number;
  removeLine: (id: string) => void;
};

export const CartContext = createContext<CartContextValue | null>(null);
