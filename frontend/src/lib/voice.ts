/**
 * Lector de la narración: pide el audio al servidor de voz (Kokoro) frase a frase, para empezar a
 * hablar enseguida, y si no hay servidor usa la voz del navegador.
 */

export interface VoiceStatus {
  available: boolean;
  voices: string[];
  default: string;
  message: string;
}

export interface SpeakOptions {
  voice: string; // voz del servidor; vacía = la de por defecto
  speed: number;
  serverAvailable: boolean;
  /** Voz distinta para un personaje (PNJ que habla). */
  speaker?: string | null;
  serverVoices?: string[];
}

/** Trocea en frases y las agrupa hasta ~260 caracteres (el audio de cada trozo tarda poco en generarse). */
export function splitForSpeech(text: string, max = 260): string[] {
  const clean = text.replace(/[*_#`]+/g, " ").replace(/\s+/g, " ").trim();
  if (!clean) return [];
  const sentences = clean.split(/(?<=[.!?…»"])\s+(?=[«"¿¡A-ZÁÉÍÓÚÑ0-9])/);
  const chunks: string[] = [];
  let current = "";
  for (const sentence of sentences) {
    if (current && (current + " " + sentence).length > max) {
      chunks.push(current);
      current = sentence;
    } else {
      current = current ? `${current} ${sentence}` : sentence;
    }
  }
  if (current) chunks.push(current);
  return chunks;
}

/** Voz alternativa estable para cada PNJ, distinta de la del narrador. */
export function voiceForSpeaker(speaker: string, narrator: string, voices: string[]): string {
  const others = voices.filter((v) => v !== narrator);
  if (others.length === 0) return narrator;
  let hash = 0;
  for (const char of speaker) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  return others[hash % others.length];
}

function bestBrowserVoice(): SpeechSynthesisVoice | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return null;
  const spanish = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith("es"));
  const score = (v: SpeechSynthesisVoice) =>
    (/natural|neural|online/i.test(v.name) ? 4 : 0) + (/google/i.test(v.name) ? 2 : 0) + (v.lang.toLowerCase() === "es-es" ? 1 : 0);
  return spanish.sort((a, b) => score(b) - score(a))[0] ?? null;
}

type Job = { text: string; options: SpeakOptions };

class NarrationVoice {
  private queue: Job[] = [];
  private running = false;
  private audio: HTMLAudioElement | null = null;
  private generation = 0;

  speak(text: string, options: SpeakOptions): void {
    for (const chunk of splitForSpeech(text)) this.queue.push({ text: chunk, options });
    if (!this.running) void this.run();
  }

  stop(): void {
    this.generation += 1;
    this.queue = [];
    this.audio?.pause();
    this.audio = null;
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    this.running = false;
  }

  private async fetchAudio(job: Job): Promise<string | null> {
    if (!job.options.serverAvailable) return null;
    const narrator = job.options.voice;
    const voice = job.options.speaker && narrator ? voiceForSpeaker(job.options.speaker, narrator, job.options.serverVoices ?? []) : narrator;
    try {
      const response = await fetch("/api/voice/speech", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: job.text, voice: voice || null, speed: job.options.speed }),
      });
      if (!response.ok) return null;
      return URL.createObjectURL(await response.blob());
    } catch {
      return null;
    }
  }

  private playUrl(url: string): Promise<void> {
    return new Promise((resolve) => {
      const audio = new Audio(url);
      this.audio = audio;
      const done = () => {
        URL.revokeObjectURL(url);
        resolve();
      };
      audio.onended = done;
      audio.onerror = done;
      audio.play().catch(done);
    });
  }

  private speakWithBrowser(job: Job): Promise<void> {
    return new Promise((resolve) => {
      if (!("speechSynthesis" in window)) return resolve();
      const utterance = new SpeechSynthesisUtterance(job.text);
      const voice = bestBrowserVoice();
      if (voice) utterance.voice = voice;
      utterance.lang = voice?.lang ?? "es-ES";
      utterance.rate = job.options.speed;
      utterance.pitch = job.options.speaker ? 0.85 : 1;
      utterance.onend = () => resolve();
      utterance.onerror = () => resolve();
      window.speechSynthesis.speak(utterance);
    });
  }

  private async run(): Promise<void> {
    this.running = true;
    const generation = this.generation;
    let next: Promise<string | null> | null = null;
    while (this.queue.length && generation === this.generation) {
      const job = this.queue.shift()!;
      const current = next ?? this.fetchAudio(job);
      // Mientras suena un trozo se genera el siguiente.
      next = this.queue.length ? this.fetchAudio(this.queue[0]) : null;
      const url = await current;
      if (generation !== this.generation) {
        if (url) URL.revokeObjectURL(url);
        break;
      }
      if (url) await this.playUrl(url);
      else await this.speakWithBrowser(job);
    }
    if (generation === this.generation) this.running = false;
  }
}

export const narrator = new NarrationVoice();
