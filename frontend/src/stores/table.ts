import { create } from "zustand";

/** Estado de la mesa compartida: quién está actuando y con qué personaje. */
interface TableState {
  activeCharacterId: string | null;
  setActiveCharacter: (id: string | null) => void;
  aiBusy: boolean;
  aiText: string;
  setAi: (busy: boolean, text?: string) => void;
}

export const useTableStore = create<TableState>((set) => ({
  activeCharacterId: null,
  setActiveCharacter: (id) => set({ activeCharacterId: id }),
  aiBusy: false,
  aiText: "",
  setAi: (busy, text = "") => set({ aiBusy: busy, aiText: text }),
}));
