import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { api } from "../../api/client";
import { usePlayers } from "../../api/hooks";
import type { AbilityKey, Attack, Character, SheetData } from "../../api/types";
import { Button, ErrorText, Field, Input, Modal, Select, TextArea } from "../../components/ui";
import { ABILITIES, DAMAGE_TYPES, SKILLS, modifier, signed } from "../../lib/rules";

const EMPTY_SHEET: SheetData = {
  abilities: { str: 10, dex: 10, con: 10, int: 10, wis: 10, cha: 10 },
  skill_proficiencies: [],
  skill_expertise: [],
  save_proficiencies: [],
  jack_of_all_trades: false,
  initiative_bonus_extra: 0,
  darkvision_ft: 0,
  resistances: [],
  immunities: [],
  vulnerabilities: [],
  attacks: [],
  spellcasting_ability: null,
  spells: [],
  spell_slots: {},
  features: [],
  feats: [],
  inventory: [],
  coins: { cp: 0, sp: 0, ep: 0, gp: 0, pp: 0 },
  languages: [],
  other_proficiencies: [],
  hit_die: "d8",
  hit_dice_used: 0,
  personality: "",
};

function linesToInventory(text: string): SheetData["inventory"] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean)
    .map((line) => {
      const match = /^(\d+)\s*[x×]\s*(.+)$/i.exec(line);
      const equipped = line.endsWith("*");
      const name = (match ? match[2] : line).replace(/\*$/, "").trim();
      return { name, quantity: match ? Number(match[1]) : 1, equipped, weight_lb: 0, notes: "" };
    });
}

function inventoryToLines(items: SheetData["inventory"]): string {
  return items.map((i) => `${i.quantity > 1 ? `${i.quantity}x ` : ""}${i.name}${i.equipped ? " *" : ""}`).join("\n");
}

export function CharacterForm({ campaignId, character, onClose }: { campaignId: string; character: Character | null; onClose: () => void }) {
  const players = usePlayers(campaignId);
  const client = useQueryClient();
  const [base, setBase] = useState({
    name: character?.name ?? "",
    player_id: character?.player_id ?? "",
    race: character?.race ?? "",
    char_class: character?.char_class ?? "",
    subclass: character?.subclass ?? "",
    level: character?.level ?? 1,
    background: character?.background ?? "",
    alignment: character?.alignment ?? "",
    xp: character?.xp ?? 0,
    hp_max: character?.hp_max ?? 10,
    armor_class: character?.armor_class ?? 10,
    speed_ft: character?.speed_ft ?? 30,
    notes: character?.notes ?? "",
  });
  const [sheet, setSheet] = useState<SheetData>({ ...EMPTY_SHEET, ...(character?.sheet ?? {}) });
  const [inventory, setInventory] = useState(inventoryToLines(sheet.inventory));
  const [features, setFeatures] = useState(sheet.features.map((f) => `${f.name}: ${f.description}`).join("\n"));
  const [spells, setSpells] = useState(sheet.spells.map((s) => `${s.name} (${s.level})`).join("\n"));

  const toggle = (list: string[], value: string) => (list.includes(value) ? list.filter((v) => v !== value) : [...list, value]);

  const save = useMutation({
    mutationFn: () => {
      const fullSheet: SheetData = {
        ...sheet,
        inventory: linesToInventory(inventory),
        features: features
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean)
          .map((l) => {
            const [name, ...rest] = l.split(":");
            return { name: name.trim(), description: rest.join(":").trim(), uses_max: null, uses_used: 0 };
          }),
        spells: spells
          .split("\n")
          .map((l) => l.trim())
          .filter(Boolean)
          .map((l) => {
            const match = /^(.*?)\s*\((\d)\)\s*$/.exec(l);
            return { name: match ? match[1] : l, level: match ? Number(match[2]) : 0, prepared: true, description: "" };
          }),
      };
      const body = { ...base, player_id: base.player_id || null, sheet: fullSheet };
      if (character) {
        return api(`/campaigns/${campaignId}/characters/${character.id}`, { method: "PATCH", body: { ...body, version: character.version }, campaignId });
      }
      return api(`/campaigns/${campaignId}/characters`, { method: "POST", body, campaignId });
    },
    onSuccess: onClose,
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });

  const remove = useMutation({
    mutationFn: () => api(`/campaigns/${campaignId}/characters/${character?.id}`, { method: "DELETE", campaignId }),
    onSuccess: onClose,
    onSettled: () => client.invalidateQueries({ queryKey: ["c", campaignId] }),
  });

  const text = (key: keyof typeof base) => ({
    value: String(base[key]),
    onChange: (e: { target: { value: string } }) => setBase({ ...base, [key]: typeof base[key] === "number" ? Number(e.target.value) : e.target.value }),
  });

  const setAttack = (index: number, patch: Partial<Attack>) =>
    setSheet({ ...sheet, attacks: sheet.attacks.map((a, i) => (i === index ? { ...a, ...patch } : a)) });

  return (
    <Modal title={character ? `Editar ${character.name}` : "Nuevo personaje"} onClose={onClose} wide>
      <form
        className="flex flex-col gap-5"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate();
        }}
      >
        <div className="grid gap-3 sm:grid-cols-4">
          <Field label="Nombre">
            <Input required {...text("name")} />
          </Field>
          <Field label="Participante">
            <Select value={base.player_id} onChange={(e) => setBase({ ...base, player_id: e.target.value })}>
              <option value="">— ninguno —</option>
              {players.data?.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.display_name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Especie / raza">
            <Input {...text("race")} />
          </Field>
          <Field label="Clase">
            <Input {...text("char_class")} />
          </Field>
          <Field label="Subclase">
            <Input {...text("subclass")} />
          </Field>
          <Field label="Nivel">
            <Input type="number" min={1} max={20} {...text("level")} />
          </Field>
          <Field label="Trasfondo">
            <Input {...text("background")} />
          </Field>
          <Field label="Alineamiento">
            <Input {...text("alignment")} />
          </Field>
          <Field label="PG máximos">
            <Input type="number" min={1} {...text("hp_max")} />
          </Field>
          <Field label="Clase de armadura">
            <Input type="number" min={1} {...text("armor_class")} />
          </Field>
          <Field label="Velocidad (pies)">
            <Input type="number" min={0} step={5} {...text("speed_ft")} />
          </Field>
          <Field label="Visión en la oscuridad (pies)">
            <Input type="number" min={0} step={10} value={sheet.darkvision_ft} onChange={(e) => setSheet({ ...sheet, darkvision_ft: Number(e.target.value) })} />
          </Field>
        </div>

        <fieldset>
          <legend className="mb-2 font-display text-sm text-gold">Características y salvaciones</legend>
          <div className="grid grid-cols-3 gap-3 sm:grid-cols-6">
            {ABILITIES.map((a) => (
              <div key={a.key} className="rounded border border-line p-2 text-center">
                <div className="text-xs text-parchment-dim">{a.name}</div>
                <Input
                  type="number"
                  min={1}
                  max={30}
                  value={sheet.abilities[a.key]}
                  onChange={(e) => setSheet({ ...sheet, abilities: { ...sheet.abilities, [a.key]: Number(e.target.value) } })}
                  className="text-center"
                />
                <div className="text-sm">{signed(modifier(sheet.abilities[a.key]))}</div>
                <label className="mt-1 flex items-center justify-center gap-1 text-xs">
                  <input
                    type="checkbox"
                    checked={sheet.save_proficiencies.includes(a.key)}
                    onChange={() => setSheet({ ...sheet, save_proficiencies: toggle(sheet.save_proficiencies, a.key) as AbilityKey[] })}
                  />
                  salvación
                </label>
              </div>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="mb-2 font-display text-sm text-gold">Habilidades (● competencia · ◆ pericia)</legend>
          <div className="grid gap-1 text-sm sm:grid-cols-3">
            {Object.entries(SKILLS).map(([key, info]) => (
              <div key={key} className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={sheet.skill_proficiencies.includes(key)}
                  onChange={() => setSheet({ ...sheet, skill_proficiencies: toggle(sheet.skill_proficiencies, key) })}
                  aria-label={`Competencia en ${info.label}`}
                />
                <input
                  type="checkbox"
                  checked={sheet.skill_expertise.includes(key)}
                  onChange={() => setSheet({ ...sheet, skill_expertise: toggle(sheet.skill_expertise, key) })}
                  aria-label={`Pericia en ${info.label}`}
                />
                <span>
                  {info.label} <span className="text-parchment-dim">({ABILITIES.find((a) => a.key === info.ability)?.short})</span>
                </span>
              </div>
            ))}
          </div>
          <label className="mt-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={sheet.jack_of_all_trades} onChange={(e) => setSheet({ ...sheet, jack_of_all_trades: e.target.checked })} />
            Polivalente (bardo)
          </label>
        </fieldset>

        <fieldset>
          <legend className="mb-2 font-display text-sm text-gold">Ataques</legend>
          {sheet.attacks.map((attack, i) => (
            <div key={i} className="mb-2 grid grid-cols-2 gap-2 sm:grid-cols-6">
              <Input placeholder="Arma" value={attack.name} onChange={(e) => setAttack(i, { name: e.target.value })} />
              <Select value={attack.ability} onChange={(e) => setAttack(i, { ability: e.target.value as AbilityKey })}>
                {ABILITIES.map((a) => (
                  <option key={a.key} value={a.key}>
                    {a.short}
                  </option>
                ))}
              </Select>
              <Input placeholder="1d8" value={attack.damage} onChange={(e) => setAttack(i, { damage: e.target.value })} />
              <Select value={attack.damage_type} onChange={(e) => setAttack(i, { damage_type: e.target.value })}>
                {Object.entries(DAMAGE_TYPES).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </Select>
              <label className="flex items-center gap-1 text-sm">
                <input type="checkbox" checked={attack.proficient} onChange={(e) => setAttack(i, { proficient: e.target.checked })} />
                competente
              </label>
              <Button type="button" variant="subtle" onClick={() => setSheet({ ...sheet, attacks: sheet.attacks.filter((_, j) => j !== i) })}>
                Quitar
              </Button>
            </div>
          ))}
          <Button
            type="button"
            onClick={() =>
              setSheet({
                ...sheet,
                attacks: [
                  ...sheet.attacks,
                  { name: "", ability: "str", proficient: true, attack_bonus_extra: 0, damage: "1d6", damage_type: "slashing", reach_ft: 5, range_ft: null, range_long_ft: null },
                ],
              })
            }
          >
            Añadir ataque
          </Button>
        </fieldset>

        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Inventario (una línea por objeto; «2x Antorcha»; «*» = equipado)">
            <TextArea rows={6} value={inventory} onChange={(e) => setInventory(e.target.value)} />
          </Field>
          <Field label="Rasgos («Nombre: descripción»)">
            <TextArea rows={6} value={features} onChange={(e) => setFeatures(e.target.value)} />
          </Field>
          <Field label="Conjuros («Nombre (nivel)»)">
            <TextArea rows={6} value={spells} onChange={(e) => setSpells(e.target.value)} />
          </Field>
        </div>
        <div className="grid gap-3 sm:grid-cols-6">
          <Field label="Aptitud mágica">
            <Select
              value={sheet.spellcasting_ability ?? ""}
              onChange={(e) => setSheet({ ...sheet, spellcasting_ability: (e.target.value || null) as AbilityKey | null })}
            >
              <option value="">—</option>
              {ABILITIES.map((a) => (
                <option key={a.key} value={a.key}>
                  {a.short}
                </option>
              ))}
            </Select>
          </Field>
          {(["pp", "gp", "sp", "cp"] as const).map((coin) => (
            <Field key={coin} label={{ pp: "Platino", gp: "Oro", sp: "Plata", cp: "Cobre" }[coin]}>
              <Input type="number" min={0} value={sheet.coins[coin]} onChange={(e) => setSheet({ ...sheet, coins: { ...sheet.coins, [coin]: Number(e.target.value) } })} />
            </Field>
          ))}
          <Field label="Experiencia">
            <Input type="number" min={0} {...text("xp")} />
          </Field>
        </div>
        <Field label="Notas">
          <TextArea rows={3} {...text("notes")} />
        </Field>
        <ErrorText error={save.error ?? remove.error} />
        <div className="flex justify-between gap-2">
          {character ? (
            <Button type="button" variant="danger" onClick={() => window.confirm(`¿Borrar a ${character.name}?`) && remove.mutate()}>
              Borrar
            </Button>
          ) : (
            <span />
          )}
          <div className="flex gap-2">
            <Button type="button" onClick={onClose}>
              Cancelar
            </Button>
            <Button variant="primary" disabled={save.isPending}>
              Guardar
            </Button>
          </div>
        </div>
      </form>
    </Modal>
  );
}
