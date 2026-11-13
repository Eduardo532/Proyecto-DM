/**
 * Lector de la narración: pide el audio al servidor de voz (Kokoro) frase a frase, para empezar a
 * hablar enseguida, y si no hay servidor usa la voz del navegador.
 *
 * - Nunca suenan dos trozos a la vez: hay una única cola y cada reproducción se puede cancelar.
 * - Con la mesa abierta en varias ventanas (pantalla compartida + portátil del DM) solo lee una:
 *   la que tiene el «turno de voz» (Web Locks). Al pulsar ▶ en otra, las demás se callan.
 * - Se puede saber qué frase suena para resaltarla en el texto.
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

export interface Speaking {
  id: string;
  index: number;
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

type Job = { id: string; index: number; text: string; options: SpeakOptions };

const LOCK = "vdm-voz";
const TAB = Math.random().toString(36).slice(2);

export class NarrationVoice {
  private queue: Job[] = [];
  private loop = 0; // identifica la cola en curso; al callar se invalida
  private cancelCurrent: (() => void) | null = null;
  private speaking: Speaking | null = null;
  private listeners = new Set<() => void>();
  private leader = true;
  private releaseLock: (() => void) | null = null;
  private channel: BroadcastChannel | null = null;

  constructor() {
    if (typeof BroadcastChannel !== "undefined") {
      this.channel = new BroadcastChannel(LOCK);
      this.channel.onmessage = (message: MessageEvent<{ type: string; tab: string }>) => {
        if (message.data.type === "manual" && message.data.tab !== TAB) this.stop();
      };
    }
  }

  // ------------------------------------------------- frase que suena ---
  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  current = (): Speaking | null => this.speaking;

  private setSpeaking(value: Speaking | null): void {
    this.speaking = value;
    for (const listener of this.listeners) listener();
  }

  // ------------------------------------------- una sola ventana lee ---
  /** Pide el turno de voz. Mientras otra ventana lo tenga, esta no lee las narraciones nuevas. */
  claim(): void {
    const locks = typeof navigator !== "undefined" ? navigator.locks : undefined;
    if (!locks || this.releaseLock) return;
    this.leader = false;
    void locks.request(LOCK, () => {
      this.leader = true;
      return new Promise<void>((resolve) => {
        this.releaseLock = () => {
          this.leader = false;
          this.releaseLock = null;
          resolve();
        };
      });
    });
  }

  release(): void {
    this.releaseLock?.();
    this.leader = true;
  }

  isLeader(): boolean {
    return this.leader;
  }

  // ----------------------------------------------------------- cola ---
  /** Añade un texto a la cola. ``manual`` (botón ▶) suena aunque no tenga el turno y calla a las demás. */
  speak(id: string, text: string, options: SpeakOptions, manual = false): void {
    if (!manual && !this.leader) return;
    if (manual) this.channel?.postMessage({ type: "manual", tab: TAB });
    const chunks = splitForSpeech(text);
    chunks.forEach((chunk, index) => this.queue.push({ id, index, text: chunk, options }));
    if (!this.cancelCurrent && this.queue.length) void this.run(++this.loop);
  }

  stop(): void {
    this.loop += 1;
    this.queue = [];
    const cancel = this.cancelCurrent;
    this.cancelCurrent = null;
    cancel?.();
    if (typeof window !== "undefined" && "speechSynthesis" in window) window.speechSynthesis.cancel();
    this.setSpeaking(null);
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

  /** Reproduce un audio y termina al acabar, al fallar o al cancelarlo (nunca se queda colgada). */
  private play(url: string): Promise<void> {
    return new Promise((resolve) => {
      const audio = new Audio(url);
      let finished = false;
      const finish = () => {
        if (finished) return;
        finished = true;
        audio.onended = audio.onerror = null;
        audio.pause();
        URL.revokeObjectURL(url);
        resolve();
      };
      this.cancelCurrent = finish;
      audio.onended = finish;
      audio.onerror = finish;
      audio.play().catch(finish);
    });
  }

  private speakWithBrowser(job: Job): Promise<void> {
    return new Promise((resolve) => {
      if (!("speechSynthesis" in window)) return resolve();
      let finished = false;
      const finish = () => {
        if (finished) return;
        finished = true;
        resolve();
      };
      const utterance = new SpeechSynthesisUtterance(job.text);
      const voice = bestBrowserVoice();
      if (voice) utterance.voice = voice;
      utterance.lang = voice?.lang ?? "es-ES";
      utterance.rate = job.options.speed;
      utterance.pitch = job.options.speaker ? 0.85 : 1;
      utterance.onend = finish;
      utterance.onerror = finish;
      this.cancelCurrent = () => {
        window.speechSynthesis.cancel();
        finish();
      };
      window.speechSynthesis.speak(utterance);
    });
  }

  private async run(loop: number): Promise<void> {
    this.cancelCurrent = () => undefined; // marca la cola como ocupada desde ya
    let prefetched: { job: Job; audio: Promise<string | null> } | null = null;
    while (this.queue.length && loop === this.loop) {
      const job = this.queue.shift()!;
      const audio: Promise<string | null> = prefetched?.job === job ? prefetched.audio : this.fetchAudio(job);
      const upcoming = this.queue[0];
      // Mientras suena un trozo se genera el siguiente.
      prefetched = upcoming ? { job: upcoming, audio: this.fetchAudio(upcoming) } : null;
      const url = await audio;
      if (loop !== this.loop) {
        if (url) URL.revokeObjectURL(url);
        break;
      }
      this.setSpeaking({ id: job.id, index: job.index });
      if (url) await this.play(url);
      else await this.speakWithBrowser(job);
    }
    if (prefetched) void prefetched.audio.then((url) => url && URL.revokeObjectURL(url));
    if (loop === this.loop) {
      this.cancelCurrent = null;
      this.setSpeaking(null);
    }
  }
}

export const narrator = new NarrationVoice();
