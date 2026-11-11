import { useState } from "react";

import { useCampaignMutation, useEntities, useMaps, useNpcs, useScenes, useSession } from "../../api/hooks";
import type { EntityView, Npc } from "../../api/types";
import { Badge, Button, Empty, ErrorText, Field, Input, Panel, Select, TextArea } from "../../components/ui";

const EMPTY = {
  kind: "creature",
  npc_id: "",
  name: "",
  name_public: "",
  scene_id: "",
  map_id: "",
  hp_max: 7,
  armor_class: 12,
  disposition: "hostile",
  hidden: false,
  token_color: "#8b1e1e",
  attack_name: "Cimitarra",
  attack_bonus: 4,
  damage: "1d6+2",
  damage_type: "slashing",
  dex: 14,
  speed_ft: 30,
};

export function DmEntities({ campaignId }: { campaignId: string }) {
  const entities = useEntities(campaignId);
  const scenes = useScenes(campaignId);
  const maps = useMaps(campaignId);
  const npcs = useNpcs(campaignId);
  const session = useSession(campaignId);
  const [form, setForm] = useState(EMPTY);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const create = useCampaignMutation<Record<string, unknown>>(campaignId, "POST", "/entities");
  const update = useCampaignMutation<{ id: string } & Record<string, unknown>>(campaignId, "PATCH", (b) => `/entities/${b.id}`);
  const remove = useCampaignMutation<string>(campaignId, "DELETE", (id) => `/entities/${id}`);
  const startCombat = useCampaignMutation<{ entity_ids: string[] }>(campaignId, "POST", "/combat");
  const list = entities.data ?? [];
  const sceneName = (id: string | null) => scenes.data?.find((s) => s.id === id)?.name ?? "—";

  const toggle = (id: string) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  return (
    <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="flex flex-col gap-4">
        <Panel
          title="Criaturas, PNJ y personajes en escena"
          actions={
            <Button variant="danger" disabled={selected.size < 2 || !session.data} onClick={() => startCombat.mutate({ entity_ids: [...selected] }, { onSuccess: () => setSelected(new Set()) })}>
              Iniciar combate ({selected.size})
            </Button>
          }
        >
          {list.length === 0 && <Empty>Sin entidades.</Empty>}
          <table className="w-full text-sm">
            <thead className="text-left text-parchment-dim">
              <tr>
                <th />
                <th>Nombre</th>
                <th>Escena</th>
                <th>Casilla</th>
                <th>PG</th>
                <th>Estado</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {list.map((e) => (
                <EntityRow
                  key={e.id}
                  entity={e}
                  sceneName={sceneName(e.scene_id)}
                  checked={selected.has(e.id)}
                  onCheck={() => toggle(e.id)}
                  onHide={() => update.mutate({ id: e.id, hidden: !e.hidden })}
                  onHp={(hp) => update.mutate({ id: e.id, hp_current: hp })}
                  onDelete={() => window.confirm(`¿Quitar ${e.name}?`) && remove.mutate(e.id)}
                />
              ))}
            </tbody>
          </table>
          <ErrorText error={update.error ?? remove.error ?? startCombat.error} />
          <p className="mt-2 text-xs text-parchment-dim">Para colocar una criatura en el mapa: créala aquí con su escena y mapa, y muévela desde la pestaña Mapa en modo DM.</p>
        </Panel>
        <NpcPanel campaignId={campaignId} />
      </div>
      <Panel title="Nueva criatura u objeto">
        <form
          className="flex flex-col gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const { attack_name, attack_bonus, damage, damage_type, dex, speed_ft, ...rest } = form;
            create.mutate(
              {
                ...rest,
                scene_id: rest.scene_id || null,
                npc_id: rest.kind === "npc" && rest.npc_id ? rest.npc_id : null,
                map_id: rest.map_id || null,
                stats: { attack_name, attack_bonus, damage, damage_type, dex, speed_ft },
              },
              { onSuccess: () => setForm({ ...EMPTY, scene_id: form.scene_id, map_id: form.map_id }) },
            );
          }}
        >
          <div className="grid grid-cols-2 gap-2">
            <Field label="Nombre real">
              <Input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </Field>
            <Field label="Nombre para la mesa">
              <Input placeholder="Figura encapuchada" value={form.name_public} onChange={(e) => setForm({ ...form, name_public: e.target.value })} />
            </Field>
            <Field label="Tipo">
              <Select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
                <option value="creature">Criatura</option>
                <option value="npc">PNJ</option>
                <option value="object">Objeto</option>
              </Select>
            </Field>
            {form.kind === "npc" && (
              <Field label="Identidad del PNJ">
                <Select value={form.npc_id} onChange={(e) => setForm({ ...form, npc_id: e.target.value })}>
                  <option value="">—</option>
                  {npcs.data?.map((n) => (
                    <option key={n.id} value={n.id}>
                      {n.name}
                    </option>
                  ))}
                </Select>
              </Field>
            )}
            <Field label="Actitud">
              <Select value={form.disposition} onChange={(e) => setForm({ ...form, disposition: e.target.value })}>
                <option value="hostile">Hostil</option>
                <option value="neutral">Neutral</option>
                <option value="ally">Aliado</option>
              </Select>
            </Field>
            <Field label="Escena">
              <Select value={form.scene_id} onChange={(e) => setForm({ ...form, scene_id: e.target.value })}>
                <option value="">—</option>
                {scenes.data?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Mapa">
              <Select value={form.map_id} onChange={(e) => setForm({ ...form, map_id: e.target.value })}>
                <option value="">—</option>
                {maps.data?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="PG">
              <Input type="number" min={1} value={form.hp_max} onChange={(e) => setForm({ ...form, hp_max: Number(e.target.value) })} />
            </Field>
            <Field label="CA">
              <Input type="number" min={1} value={form.armor_class} onChange={(e) => setForm({ ...form, armor_class: Number(e.target.value) })} />
            </Field>
            <Field label="Ataque">
              <Input value={form.attack_name} onChange={(e) => setForm({ ...form, attack_name: e.target.value })} />
            </Field>
            <Field label="Bonificador de ataque">
              <Input type="number" value={form.attack_bonus} onChange={(e) => setForm({ ...form, attack_bonus: Number(e.target.value) })} />
            </Field>
            <Field label="Daño">
              <Input value={form.damage} onChange={(e) => setForm({ ...form, damage: e.target.value })} />
            </Field>
            <Field label="Destreza">
              <Input type="number" min={1} max={30} value={form.dex} onChange={(e) => setForm({ ...form, dex: Number(e.target.value) })} />
            </Field>
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.hidden} onChange={(e) => setForm({ ...form, hidden: e.target.checked })} />
            Oculta (la mesa no la ve hasta que la reveles)
          </label>
          <ErrorText error={create.error} />
          <Button variant="primary">Añadir</Button>
        </form>
      </Panel>
    </div>
  );
}

function EntityRow({
  entity,
  sceneName,
  checked,
  onCheck,
  onHide,
  onHp,
  onDelete,
}: {
  entity: EntityView;
  sceneName: string;
  checked: boolean;
  onCheck: () => void;
  onHide: () => void;
  onHp: (hp: number) => void;
  onDelete: () => void;
}) {
  return (
    <tr className="border-t border-line/50">
      <td>
        <input type="checkbox" checked={checked} onChange={onCheck} aria-label={`Seleccionar ${entity.name}`} />
      </td>
      <td>
        {entity.name}
        {entity.name_public && <span className="text-parchment-dim"> ({entity.name_public})</span>}{" "}
        {entity.disposition === "hostile" && <Badge tone="blood">hostil</Badge>}
      </td>
      <td>{sceneName}</td>
      <td>{entity.x !== null ? `${entity.x},${entity.y}` : "—"}</td>
      <td>
        {entity.kind === "character" ? (
          "ficha"
        ) : (
          <input
            type="number"
            className="w-16 rounded border border-line bg-ink px-1"
            defaultValue={entity.hp_current ?? 0}
            onBlur={(e) => onHp(Number(e.target.value))}
          />
        )}
        {entity.hp_max ? <span className="text-parchment-dim">/{entity.hp_max}</span> : null}
      </td>
      <td>{entity.hidden ? <Badge tone="arcane">oculta</Badge> : <Badge>visible</Badge>}</td>
      <td className="whitespace-nowrap">
        {entity.kind !== "character" && (
          <>
            <Button variant="subtle" onClick={onHide}>
              {entity.hidden ? "Revelar" : "Ocultar"}
            </Button>
            <Button variant="subtle" onClick={onDelete}>
              ✕
            </Button>
          </>
        )}
      </td>
    </tr>
  );
}

function NpcPanel({ campaignId }: { campaignId: string }) {
  const npcs = useNpcs(campaignId);
  const [editing, setEditing] = useState<Partial<Npc> | null>(null);
  const save = useCampaignMutation<Partial<Npc>>(campaignId, editing?.id ? "PUT" : "POST", editing?.id ? `/npcs/${editing.id}` : "/npcs");
  return (
    <Panel title="PNJ (identidad, personalidad y secretos)" actions={<Button onClick={() => setEditing({ name: "", attitude: "indifferent", status: "alive" })}>Nuevo PNJ</Button>}>
      <ul className="flex flex-col gap-1">
        {npcs.data?.map((n) => (
          <li key={n.id}>
            <button className="text-left hover:text-gold" onClick={() => setEditing(n)}>
              <strong>{n.name}</strong> <span className="text-sm text-parchment-dim">{n.attitude} · {n.status}</span>
            </button>
          </li>
        ))}
      </ul>
      {editing && (
        <form
          className="mt-4 flex flex-col gap-2 border-t border-line pt-4"
          onSubmit={(e) => {
            e.preventDefault();
            save.mutate(editing, { onSuccess: () => setEditing(null) });
          }}
        >
          <Input placeholder="Nombre" required value={editing.name ?? ""} onChange={(e) => setEditing({ ...editing, name: e.target.value })} />
          <TextArea rows={2} placeholder="Descripción visible" value={editing.public_description ?? ""} onChange={(e) => setEditing({ ...editing, public_description: e.target.value })} />
          <TextArea rows={2} placeholder="Personalidad" value={editing.personality ?? ""} onChange={(e) => setEditing({ ...editing, personality: e.target.value })} />
          <Input placeholder="Forma de hablar" value={editing.voice ?? ""} onChange={(e) => setEditing({ ...editing, voice: e.target.value })} />
          <TextArea rows={2} placeholder="Motivaciones (solo DM)" value={editing.motivations ?? ""} onChange={(e) => setEditing({ ...editing, motivations: e.target.value })} />
          <TextArea rows={2} placeholder="Secretos (solo DM; la IA no los recibe al interpretarlo)" value={editing.secrets ?? ""} onChange={(e) => setEditing({ ...editing, secrets: e.target.value })} />
          <div className="flex gap-2">
            <Select value={editing.attitude ?? "indifferent"} onChange={(e) => setEditing({ ...editing, attitude: e.target.value })}>
              <option value="friendly">Amistoso</option>
              <option value="indifferent">Indiferente</option>
              <option value="hostile">Hostil</option>
            </Select>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={Boolean(editing.known_to_party)} onChange={(e) => setEditing({ ...editing, known_to_party: e.target.checked })} />
              Conocido por el grupo
            </label>
          </div>
          <ErrorText error={save.error} />
          <div className="flex justify-end gap-2">
            <Button type="button" onClick={() => setEditing(null)}>
              Cancelar
            </Button>
            <Button variant="primary">Guardar</Button>
          </div>
        </form>
      )}
    </Panel>
  );
}
