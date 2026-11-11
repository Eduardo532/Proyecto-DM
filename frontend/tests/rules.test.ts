import { describe, expect, it } from "vitest";

import type { GameEvent } from "../src/api/types";
import { eventSummary, outcomeLabel } from "../src/lib/events";
import { cellLabel, modifier, signed } from "../src/lib/rules";

describe("reglas en la interfaz", () => {
  it("calcula modificadores como el motor", () => {
    expect([1, 8, 9, 10, 11, 20, 30].map(modifier)).toEqual([-5, -1, -1, 0, 0, 5, 10]);
    expect(signed(3)).toBe("+3");
    expect(signed(-1)).toBe("-1");
  });

  it("etiqueta casillas como el backend", () => {
    expect(cellLabel(0, 0)).toBe("A1");
    expect(cellLabel(2, 6)).toBe("C7");
    expect(cellLabel(26, 0)).toBe("AA1");
  });
});

describe("registro de acontecimientos", () => {
  const base: GameEvent = {
    id: "1",
    seq: 1,
    type: "roll_resolved",
    actor_kind: "player",
    actor_id: null,
    payload: { label: "Atletismo — Thorin", breakdown: "d20 (12) + 5 = 17", outcome: "success" },
    visibility: "public",
    session_id: null,
    created_at: "",
  };

  it("resume una tirada", () => {
    expect(eventSummary(base)).toBe("🎲 Atletismo — Thorin: d20 (12) + 5 = 17 — éxito");
  });

  it("ignora eventos internos", () => {
    expect(eventSummary({ ...base, type: "ai_decision" })).toBeNull();
    expect(outcomeLabel("critical")).toBe("¡crítico!");
  });
});
