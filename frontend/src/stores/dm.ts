import { create } from "zustand";

/**
 * Modo DM. El token vive solo en memoria (no en localStorage): al recargar la página se
 * vuelve al modo jugadores, que es lo seguro en una pantalla compartida.
 */
interface DmState {
  tokens: Record<string, string>;
  login: (campaignId: string, token: string) => void;
  logout: (campaignId: string) => void;
}

export const useDmStore = create<DmState>((set) => ({
  tokens: {},
  login: (campaignId, token) => set((s) => ({ tokens: { ...s.tokens, [campaignId]: token } })),
  logout: (campaignId) =>
    set((s) => {
      const tokens = { ...s.tokens };
      delete tokens[campaignId];
      return { tokens };
    }),
}));

export function useIsDm(campaignId: string): boolean {
  return useDmStore((s) => Boolean(s.tokens[campaignId]));
}
