import { describe, expect, it } from "vitest";

import { splitForSpeech, voiceForSpeaker } from "../src/lib/voice";

describe("voz del DM", () => {
  it("trocea la narración en frases sin cortar palabras", () => {
    const text = "La puerta cruje. ¿Quién anda ahí? Una voz responde: «Nadie». " + "El pasillo sigue y sigue hacia la oscuridad. ".repeat(8);
    const chunks = splitForSpeech(text);
    expect(chunks[0].startsWith("La puerta cruje. ¿Quién anda ahí?")).toBe(true);
    expect(chunks.every((c) => c.length <= 260)).toBe(true);
    expect(chunks.join(" ")).toBe(text.replace(/\s+/g, " ").trim());
    expect(splitForSpeech("  **  ")).toEqual([]);
  });

  it("cada PNJ tiene siempre la misma voz y distinta de la del narrador", () => {
    const voices = ["em_alex", "em_santa", "ef_dora"];
    const voice = voiceForSpeaker("Posadero", "em_alex", voices);
    expect(voice).not.toBe("em_alex");
    expect(voiceForSpeaker("Posadero", "em_alex", voices)).toBe(voice);
    expect(voiceForSpeaker("Posadero", "em_alex", ["em_alex"])).toBe("em_alex");
  });
});

describe("cola de lectura", () => {
  it("nunca reproduce dos trozos a la vez y al callar no deja nada sonando", async () => {
    const { NarrationVoice } = await import("../src/lib/voice");
    const playing = new Set<FakeAudio>();
    let maxPlaying = 0;
    class FakeAudio {
      onended: (() => void) | null = null;
      onerror: (() => void) | null = null;
      constructor(public src: string) {}
      play() {
        playing.add(this);
        maxPlaying = Math.max(maxPlaying, playing.size);
        setTimeout(() => {
          if (playing.has(this)) {
            playing.delete(this);
            this.onended?.();
          }
        }, 5);
        return Promise.resolve();
      }
      pause() {
        playing.delete(this);
      }
    }
    const originalAudio = globalThis.Audio;
    const originalFetch = globalThis.fetch;
    const originalUrl = URL.createObjectURL;
    globalThis.Audio = FakeAudio as unknown as typeof Audio;
    globalThis.fetch = (async () => new Response(new Blob(["x"]), { status: 200 })) as typeof fetch;
    URL.createObjectURL = () => "blob:x";
    URL.revokeObjectURL = () => undefined;
    try {
      const voice = new NarrationVoice();
      const seen: (string | null)[] = [];
      voice.subscribe(() => seen.push(voice.current() ? `${voice.current()!.id}:${voice.current()!.index}` : null));
      const options = { voice: "em_alex", speed: 1, serverAvailable: true };
      voice.speak("a", "Primera frase. Segunda frase.".repeat(20), options);
      voice.speak("b", "Otra narración que llega mientras tanto.", options);
      voice.speak("c", "Y otra más.", options, true);
      await new Promise((r) => setTimeout(r, 400));
      expect(maxPlaying).toBe(1);
      expect(seen.filter(Boolean)[0]).toBe("a:0");
      expect(seen).toContain("c:0");
      expect(voice.current()).toBeNull();

      voice.speak("d", "Una frase larga. ".repeat(40), options);
      await new Promise((r) => setTimeout(r, 2));
      voice.stop();
      await new Promise((r) => setTimeout(r, 50));
      expect(playing.size).toBe(0);
      expect(voice.current()).toBeNull();
    } finally {
      globalThis.Audio = originalAudio;
      globalThis.fetch = originalFetch;
      URL.createObjectURL = originalUrl;
    }
  });
});
