import { describe, expect, it } from "vitest";

// Código fuente de la interfaz como texto (Vite lo resuelve en las pruebas).
const sources = import.meta.glob("../src/**/*.{ts,tsx}", { query: "?raw", import: "default", eager: true }) as Record<string, string>;

describe("efectos de React", () => {
  it("ningún efecto devuelve el valor de una expresión (React lo trataría como función de limpieza)", () => {
    // Ejemplo real: scrollIntoView devuelve una promesa en navegadores recientes y dejaba la página en blanco.
    const offenders = Object.entries(sources).flatMap(([file, text]) =>
      [...text.matchAll(/use(?:Layout)?Effect\(\s*\(\)\s*=>(?!\s*\{)/g)].map((m) => `${file}: ${text.slice(m.index, m.index + 80)}`),
    );
    expect(Object.keys(sources).length).toBeGreaterThan(10);
    expect(offenders).toEqual([]);
  });
});
