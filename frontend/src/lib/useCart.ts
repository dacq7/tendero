"use client";

// Carrito persistido en sessionStorage: sobrevive a la navegación dentro de la app
// (y a una recarga), encaja con el BFF (estado de cliente, sin servidor) y se
// limpia al cerrar la pestaña. La lógica de mutación es pura (lib/cart.ts).

import { useEffect, useState } from "react";

import { addToCart, type CartLine, type Product, removeFromCart, setCantidad } from "./cart";

const KEY = "tendero_cart";

function load(): CartLine[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as CartLine[]) : [];
  } catch {
    return [];
  }
}

export interface CartStore {
  cart: CartLine[];
  add: (product: Product) => void;
  cambiarCantidad: (productId: number, cantidad_milesimas: number) => void;
  quitar: (productId: number) => void;
  vaciar: () => void;
}

export function useCart(): CartStore {
  // Inicializador perezoso (en render, no en effect): restaura el carrito al montar.
  const [cart, setCart] = useState<CartLine[]>(load);

  useEffect(() => {
    try {
      window.sessionStorage.setItem(KEY, JSON.stringify(cart));
    } catch {
      /* sessionStorage no disponible: el carrito sigue en memoria */
    }
  }, [cart]);

  return {
    cart,
    add: (product) => setCart((c) => addToCart(c, product)),
    cambiarCantidad: (productId, ml) => setCart((c) => setCantidad(c, productId, ml)),
    quitar: (productId) => setCart((c) => removeFromCart(c, productId)),
    vaciar: () => setCart([]),
  };
}
