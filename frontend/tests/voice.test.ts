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
