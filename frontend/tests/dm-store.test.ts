import { describe, expect, it } from "vitest";

import { useDmStore } from "../src/stores/dm";

describe("modo DM", () => {
  it("al salir se borra el token de esa campaña y no el de otras", () => {
    const store = useDmStore.getState();
    store.login("a", "token-a");
    store.login("b", "token-b");
    useDmStore.getState().logout("a");
    expect(useDmStore.getState().tokens).toEqual({ b: "token-b" });
  });
});
