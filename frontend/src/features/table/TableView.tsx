import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { api } from "../../api/client";
import {
  useCampaign,
  useCharacters,
  useEvents,
  useFacts,
  usePendingRolls,
  usePlayers,
  useQuests,
  useScenes,
  useSession,
} from "../../api/hooks";
import type { Character, GameEvent, Player, Roll } from "../../api/types";
import { Badge, Button, Empty, ErrorText, HpBar, Input, Panel } from "../../components/ui";
import { eventSummary, outcomeLabel } from "../../lib/events";
import { CONDITIONS, signed } from "../../lib/rules";
import { useTableStore } from "../../stores/table";

export function TableView({ campaignId }: { campaignId: string }) {
  return (
    <div className="grid h-full gap-4 pt-1 lg:grid-cols-[260px_minmax(0,1fr)_300px]">
      <PartyPanel campaignId={campaignId} />
      <div className="flex min-h-0 flex-col gap-3">
        <StartAdventure campaignId={campaignId} />
        <Narration campaignId={campaignId} />
        <PendingRolls campaignId={campaignId} />
        <ActionBar campaignId={campaignId} />
      </div>
      <SidePanel campaignId={campaignId} />
    </div>
  );
}

function PartyPanel({ campaignId }: { campaignId: string }) {
  const players = usePlayers(campaignId);
  const characters = useCharacters(campaignId);
  const session = useSession(campaignId);
  const { activeCharacterId, setActiveCharacter } = useTableStore();
  const client = useQueryClient();
  const setActivePlayer = useMutation({
    mutationFn: (playerId: string) =>
      api(`/campaigns/${campaignId}/sessions/${session.data?.id}`, { method: "PATCH", body: { active_player_id: playerId }, campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const list = players.data ?? [];
  const activePlayerId = session.data?.active_player_id ?? null;

  const choosePlayer = (player: Player) => {
    const own = (characters.data ?? []).find((c) => c.player_id === player.id && c.status === "active");
    if (own) setActiveCharacter(own.id);
    if (session.data) setActivePlayer.mutate(player.id);
  };

  const next = () => {
    if (list.length === 0) return;
    const index = list.findIndex((p) => p.id === activePlayerId);
    choosePlayer(list[(index + 1) % list.length]);
  };

  return (
    <Panel title="Mesa" actions={<Button onClick={next} disabled={list.length < 2}>Siguiente →</Button>} className="h-fit">
      {list.length === 0 && <Empty>Añade participantes en la pestaña Personajes.</Empty>}
      <ol className="flex flex-col gap-3">
        {list.map((player) => {
          const own = (characters.data ?? []).filter((c) => c.player_id === player.id);
          const isActive = player.id === activePlayerId;
          return (
            <li key={player.id} className={`rounded-md border p-2 ${isActive ? "border-gold bg-gold/10" : "border-line"}`}>
              <button className="flex w-full items-center gap-2 text-left" onClick={() => choosePlayer(player)}>
                <span className="h-3 w-3 rounded-full" style={{ background: player.color }} />
                <span className="font-semibold">{player.display_name}</span>
                {isActive && <Badge tone="gold">activo</Badge>}
              </button>
              {own.map((c) => (
                <CharacterLine key={c.id} character={c} selected={c.id === activeCharacterId} onSelect={() => setActiveCharacter(c.id)} />
              ))}
            </li>
          );
        })}
      </ol>
      {(characters.data ?? []).filter((c) => !c.player_id).length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-xs uppercase text-parchment-dim">Sin participante</p>
          {(characters.data ?? [])
            .filter((c) => !c.player_id)
            .map((c) => (
              <CharacterLine key={c.id} character={c} selected={c.id === activeCharacterId} onSelect={() => setActiveCharacter(c.id)} />
            ))}
        </div>
      )}
    </Panel>
  );
}

function CharacterLine({ character, selected, onSelect }: { character: Character; selected: boolean; onSelect: () => void }) {
  return (
    <button onClick={onSelect} className={`mt-2 block w-full rounded px-2 py-1 text-left ${selected ? "bg-ink-3 ring-1 ring-gold" : "hover:bg-ink-3"}`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-serif text-lg">{character.name}</span>
        <span className="text-xs text-parchment-dim">CA {character.armor_class}</span>
      </div>
      <HpBar current={character.hp_current} max={character.hp_max} temp={character.hp_temp} />
      {character.conditions.length > 0 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {character.conditions.map((c) => (
            <Badge key={c} tone="blood">
              {CONDITIONS[c] ?? c}
            </Badge>
          ))}
        </div>
      )}
    </button>
  );
}

/** Botón para empezar: el DM presenta la historia y la primera escena. Desaparece cuando ya empezó. */
function StartAdventure({ campaignId }: { campaignId: string }) {
  const events = useEvents(campaignId);
  const aiBusy = useTableStore((s) => s.aiBusy);
  const client = useQueryClient();
  const start = useMutation({
    mutationFn: () => api(`/campaigns/${campaignId}/start`, { method: "POST", campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const started = (events.data ?? []).some(
    (e) => e.type === "campaign_started" || (e.type === "narration" && ["intro", "scene", "recap"].includes(String((e.payload as Record<string, unknown>).kind))),
  );
  if (!events.data || started) return null;
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border-2 border-gold bg-ink-2 p-6 text-center">
      <span className="text-4xl">📖</span>
      <h2 className="font-display text-2xl text-gold">¿Empezamos la aventura?</h2>
      <p className="max-w-xl font-serif text-parchment-dim">
        El DM presentará la historia, os situará en la primera escena y os preguntará qué hacéis. Después cada jugador puede actuar o simplemente hablar: con los
        personajes del mundo, con el grupo o con el propio DM.
      </p>
      <Button variant="primary" className="px-6 py-3 text-lg" onClick={() => start.mutate()} disabled={start.isPending || aiBusy}>
        {start.isPending || aiBusy ? "El DM está preparando la historia…" : "Comenzar la aventura"}
      </Button>
      <ErrorText error={start.error} />
    </div>
  );
}

function Narration({ campaignId }: { campaignId: string }) {
  const events = useEvents(campaignId);
  const aiBusy = useTableStore((s) => s.aiBusy);
  const bottom = useRef<HTMLDivElement>(null);
  const items = useMemo(() => (events.data ?? []).filter((e) => e.type === "narration" || e.type === "player_action" || eventSummary(e)), [events.data]);
  useEffect(() => {
    // Llaves obligatorias: en navegadores recientes scrollIntoView devuelve una promesa y React
    // la tomaría por la función de limpieza del efecto (pantalla en blanco al abrir la campaña).
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [items.length, aiBusy]);

  return (
    <section className="min-h-[320px] flex-1 overflow-y-auto rounded-lg border border-line bg-[#efe5cc] px-6 py-5 text-ink shadow-inner scroll-thin">
      {items.length === 0 && (
        <p className="font-serif text-lg italic text-[#5b4a36]">
          Pulsa «Comenzar la aventura» para que el DM presente la historia. Después, cada jugador escribe lo que hace o dice su personaje.
        </p>
      )}
      {items.map((event) => (
        <NarrationItem key={event.id} event={event} />
      ))}
      {aiBusy && <p className="animate-pulse font-serif italic text-[#7a6446]">El DM está pensando…</p>}
      <div ref={bottom} />
    </section>
  );
}

function NarrationItem({ event }: { event: GameEvent }) {
  const p = event.payload as Record<string, unknown>;
  if (event.type === "narration") {
    const kind = String(p.kind ?? "");
    const speaker = p.speaker ? String(p.speaker) : null;
    return (
      <div className={`mb-4 whitespace-pre-line font-serif text-xl leading-relaxed ${kind === "scene" || kind === "intro" ? "read-aloud" : ""} ${kind === "roll_prompt" ? "font-semibold text-[#7a2020]" : ""}`}>
        {speaker && <span className="mr-2 font-display text-sm text-[#7a5a20]">{speaker}:</span>}
        {String(p.text ?? "")}
      </div>
    );
  }
  if (event.type === "player_action") {
    if (p.mode === "talk") {
      return (
        <p className="mb-3 border-l-4 border-[#5a7a9a] pl-3 font-serif text-lg text-[#2f3f52]">
          <strong>{String(p.name)}</strong> dice: «{String(p.text)}»
        </p>
      );
    }
    return (
      <p className="mb-3 border-l-4 border-[#b8913a] pl-3 font-serif text-lg italic text-[#4a3b28]">
        <strong className="not-italic">{String(p.name)}</strong>: {String(p.text)}
      </p>
    );
  }
  return <p className="mb-2 font-sans text-sm text-[#6b5a44]">{eventSummary(event)}</p>;
}

function PendingRolls({ campaignId }: { campaignId: string }) {
  const rolls = usePendingRolls(campaignId);
  if (!rolls.data?.length) return null;
  return (
    <div className="flex flex-col gap-2">
      {rolls.data.map((roll) => (
        <RollCard key={roll.id} campaignId={campaignId} roll={roll} />
      ))}
    </div>
  );
}

function RollCard({ campaignId, roll }: { campaignId: string; roll: Roll }) {
  const campaign = useCampaign(campaignId);
  const client = useQueryClient();
  const diceCount = roll.advantage === "none" ? 1 : 2;
  const [values, setValues] = useState<string[]>(Array(diceCount).fill(""));
  const resolve = useMutation({
    mutationFn: (body: { mode: "digital" | "manual"; values?: number[] }) =>
      api<Roll>(`/campaigns/${campaignId}/rolls/${roll.id}/resolve`, { method: "POST", body, campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const mode = campaign.data?.dice_mode ?? "ask";
  const advantageText = roll.advantage === "advantage" ? "con ventaja (2d20, el mayor)" : roll.advantage === "disadvantage" ? "con desventaja (2d20, el menor)" : "1d20";
  return (
    <div className="rounded-lg border-2 border-gold bg-ink-2 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-lg text-gold">🎲 {roll.label}</h3>
        <span className="text-sm text-parchment-dim">
          {advantageText} {signed(roll.modifier_total)}
          {roll.dc !== null ? ` · CD ${roll.dc}` : ""}
        </span>
      </div>
      {roll.reason && <p className="mt-1 font-serif italic text-parchment-dim">{roll.reason}</p>}
      <div className="mt-3 flex flex-wrap items-center gap-3">
        {mode !== "manual" && (
          <Button variant="primary" onClick={() => resolve.mutate({ mode: "digital" })} disabled={resolve.isPending}>
            Tirar dados
          </Button>
        )}
        {mode !== "digital" && (
          <form
            className="flex items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              resolve.mutate({ mode: "manual", values: values.map(Number) });
            }}
          >
            <span className="text-sm text-parchment-dim">Dado físico:</span>
            {values.map((v, i) => (
              <Input
                key={i}
                type="number"
                min={1}
                max={20}
                required
                value={v}
                className="w-20"
                onChange={(e) => setValues(values.map((old, j) => (j === i ? e.target.value : old)))}
              />
            ))}
            <Button disabled={resolve.isPending}>Registrar</Button>
          </form>
        )}
      </div>
      <ErrorText error={resolve.error} />
      {resolve.data && (
        <p className="mt-2 text-sm">
          {resolve.data.breakdown} {resolve.data.outcome ? `— ${outcomeLabel(resolve.data.outcome)}` : ""}
        </p>
      )}
    </div>
  );
}

function ActionBar({ campaignId }: { campaignId: string }) {
  const characters = useCharacters(campaignId);
  const session = useSession(campaignId);
  const players = usePlayers(campaignId);
  const { activeCharacterId, setActiveCharacter } = useTableStore();
  const [text, setText] = useState("");
  const [mode, setMode] = useState<"action" | "talk">("action");
  const [dice, setDice] = useState("");
  const client = useQueryClient();
  const living = (characters.data ?? []).filter((c) => c.status === "active");
  const acting = living.find((c) => c.id === activeCharacterId) ?? living[0];
  const send = useMutation({
    mutationFn: () =>
      api(`/campaigns/${campaignId}/actions`, {
        method: "POST",
        body: { character_id: acting?.id, player_id: acting?.player_id ?? null, text, mode },
        campaignId,
      }),
    onSuccess: () => setText(""),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const freeRoll = useMutation({
    mutationFn: () =>
      api(`/campaigns/${campaignId}/rolls/free`, { method: "POST", body: { expression: dice, character_id: acting?.id ?? null, label: dice }, campaignId }),
    onSuccess: () => setDice(""),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const blocked = !session.data || session.data.state === "awaiting_roll";
  const playerName = players.data?.find((p) => p.id === acting?.player_id)?.display_name;

  return (
    <div className="rounded-lg border border-line bg-ink-2 p-3">
      <div className="mb-2 flex gap-1" role="group" aria-label="Tipo de intervención">
        <Button type="button" variant={mode === "action" ? "primary" : "ghost"} onClick={() => setMode("action")} aria-pressed={mode === "action"}>
          🗡️ Hacer algo
        </Button>
        <Button type="button" variant={mode === "talk" ? "primary" : "ghost"} onClick={() => setMode("talk")} aria-pressed={mode === "talk"}>
          💬 Hablar
        </Button>
        <span className="self-center text-xs text-parchment-dim">
          {mode === "action" ? "El DM decide si hace falta una tirada." : "Habla con un personaje del mundo, con el grupo o pregunta al DM. Sin tiradas."}
        </span>
      </div>
      <form
        className="flex flex-wrap items-center gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (text.trim() && acting) send.mutate();
        }}
      >
        <select
          className="rounded-md border border-line bg-ink px-2 py-2 text-parchment"
          value={acting?.id ?? ""}
          onChange={(e) => setActiveCharacter(e.target.value)}
          aria-label="Personaje que actúa"
        >
          {living.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <input
          className="min-w-[240px] flex-1 rounded-md border border-line bg-ink px-3 py-2 font-serif text-lg text-parchment focus:border-gold focus:outline-none"
          placeholder={
            !session.data
              ? "Pulsa «Comenzar la aventura» para jugar"
              : blocked
                ? "Resuelve la tirada pendiente…"
                : `¿Qué ${mode === "talk" ? "dice" : "hace"} ${acting?.name ?? "tu personaje"}${playerName ? ` (${playerName})` : ""}?`
          }
          value={text}
          onChange={(e) => setText(e.target.value)}
          disabled={blocked || !acting}
        />
        <Button variant="primary" disabled={blocked || !text.trim() || send.isPending || !acting}>
          {mode === "talk" ? "Decir" : "Actuar"}
        </Button>
      </form>
      <form
        className="mt-2 flex items-center gap-2 text-sm"
        onSubmit={(e) => {
          e.preventDefault();
          if (dice.trim()) freeRoll.mutate();
        }}
      >
        <span className="text-parchment-dim">Tirada libre:</span>
        <input className="w-32 rounded border border-line bg-ink px-2 py-1" placeholder="2d6+3" value={dice} onChange={(e) => setDice(e.target.value)} />
        <Button disabled={!dice.trim() || freeRoll.isPending}>Tirar</Button>
        <ErrorText error={send.error ?? freeRoll.error} />
      </form>
    </div>
  );
}

function SidePanel({ campaignId }: { campaignId: string }) {
  const session = useSession(campaignId);
  const scenes = useScenes(campaignId);
  const facts = useFacts(campaignId);
  const quests = useQuests(campaignId);
  const scene = scenes.data?.find((s) => s.id === session.data?.scene_id);
  return (
    <div className="flex flex-col gap-4">
      <Panel title="Escena">
        {scene ? (
          <>
            <h3 className="font-serif text-xl">{scene.name}</h3>
            <p className="mt-1 text-sm text-parchment-dim">Luz: {{ bright: "brillante", dim: "tenue", dark: "oscuridad" }[scene.lighting] ?? scene.lighting}</p>
          </>
        ) : (
          <Empty>Sin escena activa.</Empty>
        )}
      </Panel>
      <Panel title="Descubierto">
        {facts.data?.length ? (
          <ul className="flex flex-col gap-2 font-serif">
            {facts.data.slice(-12).map((f) => (
              <li key={f.id}>• {f.statement}</li>
            ))}
          </ul>
        ) : (
          <Empty>Todavía nada.</Empty>
        )}
      </Panel>
      <Panel title="Misiones">
        {quests.data?.length ? (
          <ul className="flex flex-col gap-2">
            {quests.data.map((q) => (
              <li key={q.id}>
                <span className="font-serif">{q.title}</span> <Badge>{q.status}</Badge>
              </li>
            ))}
          </ul>
        ) : (
          <Empty>Ninguna conocida.</Empty>
        )}
      </Panel>
    </div>
  );
}
