import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { useCharacters, usePlayers } from "../../api/hooks";
import type { Character, Player } from "../../api/types";
import { Badge, Button, Empty, ErrorText, HpBar, Input, Panel, Select } from "../../components/ui";
import { ABILITIES, CONDITIONS, DAMAGE_TYPES, SKILLS, signed } from "../../lib/rules";
import { CharacterForm } from "./CharacterForm";

export function CharactersView({ campaignId }: { campaignId: string }) {
  const characters = useCharacters(campaignId);
  const [editing, setEditing] = useState<Character | "new" | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const current = characters.data?.find((c) => c.id === selected) ?? characters.data?.[0];

  return (
    <div className="grid gap-4 pt-1 lg:grid-cols-[300px_minmax(0,1fr)]">
      <div className="flex flex-col gap-4">
        <PlayersPanel campaignId={campaignId} />
        <Panel title="Personajes" actions={<Button variant="primary" onClick={() => setEditing("new")}>Nuevo</Button>}>
          {characters.data?.length === 0 && <Empty>Crea los personajes del grupo.</Empty>}
          <ul className="flex flex-col gap-2">
            {characters.data?.map((c) => (
              <li key={c.id}>
                <button
                  className={`w-full rounded border p-2 text-left ${current?.id === c.id ? "border-gold" : "border-line hover:border-parchment-dim"}`}
                  onClick={() => setSelected(c.id)}
                >
                  <div className="font-serif text-lg">{c.name}</div>
                  <div className="text-xs text-parchment-dim">
                    {c.race} {c.char_class} {c.level}
                    {c.status !== "active" ? ` · ${c.status}` : ""}
                  </div>
                  <HpBar current={c.hp_current} max={c.hp_max} temp={c.hp_temp} />
                </button>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
      {current ? <CharacterSheet campaignId={campaignId} character={current} onEdit={() => setEditing(current)} /> : <Empty>Selecciona un personaje.</Empty>}
      {editing && <CharacterForm campaignId={campaignId} character={editing === "new" ? null : editing} onClose={() => setEditing(null)} />}
    </div>
  );
}

function PlayersPanel({ campaignId }: { campaignId: string }) {
  const players = usePlayers(campaignId);
  const client = useQueryClient();
  const [name, setName] = useState("");
  const [color, setColor] = useState("#c9a24a");
  const add = useMutation({
    mutationFn: () => api<Player>(`/campaigns/${campaignId}/players`, { method: "POST", body: { display_name: name, color }, campaignId }),
    onSuccess: () => setName(""),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => api(`/campaigns/${campaignId}/players/${id}`, { method: "DELETE", campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  return (
    <Panel title="Participantes">
      <ul className="mb-3 flex flex-col gap-1">
        {players.data?.map((p) => (
          <li key={p.id} className="flex items-center gap-2">
            <span className="h-3 w-3 rounded-full" style={{ background: p.color }} />
            <span className="flex-1">{p.display_name}</span>
            <Button variant="subtle" onClick={() => window.confirm(`¿Quitar a ${p.display_name}?`) && remove.mutate(p.id)}>
              ✕
            </Button>
          </li>
        ))}
      </ul>
      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (name.trim()) add.mutate();
        }}
      >
        <Input placeholder="Nombre (p. ej. Eduardo)" value={name} onChange={(e) => setName(e.target.value)} />
        <input type="color" value={color} onChange={(e) => setColor(e.target.value)} className="h-9 w-10 rounded border border-line bg-ink" aria-label="Color" />
        <Button variant="primary">+</Button>
      </form>
      <ErrorText error={add.error} />
    </Panel>
  );
}

function CharacterSheet({ campaignId, character, onEdit }: { campaignId: string; character: Character; onEdit: () => void }) {
  const d = character.derived;
  const client = useQueryClient();
  const [amount, setAmount] = useState(1);
  const [damageType, setDamageType] = useState("slashing");
  const hp = useMutation({
    mutationFn: (kind: "damage" | "heal" | "temp") =>
      api(`/campaigns/${campaignId}/characters/${character.id}/hp`, { method: "POST", body: { kind, amount, damage_type: kind === "damage" ? damageType : "" }, campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const condition = useMutation({
    mutationFn: (body: { condition: string; present: boolean }) =>
      api(`/campaigns/${campaignId}/characters/${character.id}/conditions`, { method: "POST", body, campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const deathSave = useMutation({
    mutationFn: (natural: number) => api(`/campaigns/${campaignId}/characters/${character.id}/death-save?natural=${natural}`, { method: "POST", campaignId }),
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });
  const sheet = character.sheet;

  return (
    <div className="flex flex-col gap-4">
      <Panel title={character.name} actions={<Button onClick={onEdit}>Editar ficha</Button>}>
        <p className="font-serif text-lg text-parchment-dim">
          {character.race} · {character.char_class}
          {character.subclass ? ` (${character.subclass})` : ""} · nivel {character.level} · {character.background} {character.alignment && `· ${character.alignment}`}
        </p>
        <div className="mt-4 grid grid-cols-3 gap-3 text-center sm:grid-cols-6">
          {ABILITIES.map((a) => (
            <div key={a.key} className="rounded border border-line p-2">
              <div className="text-xs text-parchment-dim">{a.short}</div>
              <div className="font-display text-2xl">{signed(d?.ability_modifiers[a.key] ?? 0)}</div>
              <div className="text-sm text-parchment-dim">{sheet.abilities[a.key]}</div>
            </div>
          ))}
        </div>
        <div className="mt-4 grid grid-cols-2 gap-3 text-center sm:grid-cols-5">
          <Stat label="CA" value={character.armor_class} />
          <Stat label="Iniciativa" value={signed(d?.initiative ?? 0)} />
          <Stat label="Velocidad" value={`${character.speed_ft} pies`} />
          <Stat label="Competencia" value={signed(d?.proficiency_bonus ?? 2)} />
          <Stat label="Percepción pasiva" value={d?.passive_perception ?? 10} />
        </div>
      </Panel>

      <Panel title="Puntos de golpe y estado">
        <HpBar current={character.hp_current} max={character.hp_max} temp={character.hp_temp} />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <Input type="number" min={0} value={amount} onChange={(e) => setAmount(Number(e.target.value))} className="w-24" />
          <Select value={damageType} onChange={(e) => setDamageType(e.target.value)} className="w-40">
            {Object.entries(DAMAGE_TYPES).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </Select>
          <Button variant="danger" onClick={() => hp.mutate("damage")}>
            Daño
          </Button>
          <Button onClick={() => hp.mutate("heal")}>Curar</Button>
          <Button onClick={() => hp.mutate("temp")}>PG temporales</Button>
        </div>
        {character.hp_current === 0 && character.status === "active" && !character.stable && (
          <div className="mt-3 flex items-center gap-2 text-sm">
            <span>
              Salvaciones contra muerte: ✔ {character.death_saves.successes ?? 0} · ✘ {character.death_saves.failures ?? 0}
            </span>
            <Button onClick={() => deathSave.mutate(1 + Math.floor(Math.random() * 20))}>Tirar salvación</Button>
          </div>
        )}
        <div className="mt-3 flex flex-wrap gap-1">
          {Object.entries(CONDITIONS).map(([key, label]) => {
            const active = character.conditions.includes(key);
            return (
              <button
                key={key}
                onClick={() => condition.mutate({ condition: key, present: !active })}
                className={`rounded border px-2 py-0.5 text-xs ${active ? "border-blood bg-blood/30 text-parchment" : "border-line text-parchment-dim hover:border-parchment-dim"}`}
              >
                {label}
              </button>
            );
          })}
        </div>
        <ErrorText error={hp.error ?? condition.error ?? deathSave.error} />
      </Panel>

      <div className="grid gap-4 md:grid-cols-2">
        <Panel title="Habilidades">
          <ul className="grid grid-cols-1 gap-x-4 text-sm sm:grid-cols-2">
            {Object.entries(SKILLS).map(([key, info]) => (
              <li key={key} className="flex justify-between border-b border-line/40 py-0.5">
                <span>
                  {sheet.skill_expertise.includes(key) ? "◆ " : sheet.skill_proficiencies.includes(key) ? "● " : "○ "}
                  {info.label}
                </span>
                <span className="tabular-nums">{signed(d?.skills[key] ?? 0)}</span>
              </li>
            ))}
          </ul>
        </Panel>
        <div className="flex flex-col gap-4">
          <Panel title="Salvaciones">
            <div className="grid grid-cols-3 gap-2 text-sm">
              {ABILITIES.map((a) => (
                <span key={a.key}>
                  {sheet.save_proficiencies.includes(a.key) ? "● " : "○ "}
                  {a.short} {signed(d?.saves[a.key] ?? 0)}
                </span>
              ))}
            </div>
          </Panel>
          <Panel title="Ataques">
            {d?.attacks.length ? (
              <ul className="text-sm">
                {d.attacks.map((a) => (
                  <li key={a.name}>
                    <strong>{a.name}</strong>: {signed(a.bonus)} al ataque, {a.damage} {DAMAGE_TYPES[a.damage_type] ?? a.damage_type}
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>Sin ataques.</Empty>
            )}
            {d?.spell_save_dc && (
              <p className="mt-2 text-sm">
                CD de conjuros {d.spell_save_dc} · ataque de conjuro {signed(d.spell_attack_bonus ?? 0)}
              </p>
            )}
          </Panel>
          <Panel title="Inventario">
            {sheet.inventory.length ? (
              <ul className="text-sm">
                {sheet.inventory.map((item, i) => (
                  <li key={i}>
                    {item.quantity > 1 ? `${item.quantity}× ` : ""}
                    {item.name} {item.equipped && <Badge tone="gold">equipado</Badge>}
                  </li>
                ))}
              </ul>
            ) : (
              <Empty>Vacío.</Empty>
            )}
            <p className="mt-2 text-xs text-parchment-dim">
              {sheet.coins.pp} ppt · {sheet.coins.gp} po · {sheet.coins.sp} pp · {sheet.coins.cp} pc
            </p>
          </Panel>
        </div>
      </div>
      {(sheet.features.length > 0 || sheet.spells.length > 0) && (
        <Panel title="Rasgos y conjuros">
          {sheet.features.map((f) => (
            <p key={f.name} className="text-sm">
              <strong>{f.name}.</strong> {f.description}
            </p>
          ))}
          {sheet.spells.length > 0 && (
            <p className="mt-2 text-sm">
              Conjuros: {sheet.spells.map((s) => `${s.name}${s.level ? ` (${s.level})` : ""}`).join(", ")}
            </p>
          )}
        </Panel>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-line p-2">
      <div className="text-xs text-parchment-dim">{label}</div>
      <div className="font-display text-xl">{value}</div>
    </div>
  );
}
