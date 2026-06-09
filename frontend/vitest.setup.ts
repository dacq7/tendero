import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Desmonta el árbol de React tras cada test para que no se filtre estado/DOM.
afterEach(() => {
  cleanup();
});
