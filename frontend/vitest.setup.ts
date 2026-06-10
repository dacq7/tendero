import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// recharts usa ResizeObserver, ausente en jsdom: polyfill mínimo.
globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: () => {},
  unobserve: () => {},
  disconnect: () => {},
}));

// Desmonta el árbol de React tras cada test para que no se filtre estado/DOM.
afterEach(() => {
  cleanup();
  // El carrito vive en sessionStorage: limpiarlo entre tests evita filtraciones.
  window.sessionStorage.clear();
});
