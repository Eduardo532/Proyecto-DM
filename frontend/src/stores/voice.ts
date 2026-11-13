import { create } from "zustand";
import { persist } from "zustand/middleware";

/** Preferencias de la voz del DM (se recuerdan en este navegador). */
interface VoiceState {
  enabled: boolean;
  voice: string; // vacío = la voz por defecto del servidor o la mejor del navegador
  speed: number;
  setEnabled: (enabled: boolean) => void;
  setVoice: (voice: string) => void;
  setSpeed: (speed: number) => void;
}

export const useVoiceStore = create<VoiceState>()(
  persist(
    (set) => ({
      enabled: false,
      voice: "",
      speed: 1,
      setEnabled: (enabled) => set({ enabled }),
      setVoice: (voice) => set({ voice }),
      setSpeed: (speed) => set({ speed }),
    }),
    { name: "vdm-voz" },
  ),
);
