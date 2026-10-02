import { useContext } from "react";
import { CartContext, type CartContextValue } from "./cartContext";

export function useCart(): CartContextValue {
  const value = useContext(CartContext);
  if (!value) {
    throw new Error("useCart CartProvider ichida ishlatilishi kerak.");
  }
  return value;
}
