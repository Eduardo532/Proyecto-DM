import { useState } from "react";

import { useCampaignMutation, useMaps, useScenes, useSession } from "../../api/hooks";
import type { Scene } from "../../api/types";
import { Badge, Button, Empty, ErrorText, Field, Input, Panel, Select, TextArea } from "../../components/ui";

export function DmScenes({ campaignId }: { campaignId: string }) {
  const scenes = useScenes(campaignId);
  const session = useSession(campaignId);
  const [editing, setEditing] = useState<Scene | null>(null);
  const create = useCampaignMutation<Partial<Scene>, Scene>(campaignId, "POST", "/scenes");

  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <Panel
        title="Escenas"
        actions={
          <Button variant="primary" onClick={() => create.mutate({ name: "Nueva escena" }, { onSuccess: (s) => setEditing(s) })}>
            Nueva
          </Button>
        }
      >
        {!session.data && <p className="mb-3 text-sm text-gold">Inicia una sesión para poder activar escenas.</p>}
        {scenes.data?.length === 0 && <Empty>Sin escenas. Importa un PDF (se detectan las áreas numeradas) o crea una.</Empty>}
        <ul className="flex flex-col gap-2">
          {scenes.data?.map((s) => (
            <li key={s.id} className={`rounded border p-2 ${session.data?.scene_id === s.id ? "border-gold" : "border-line"}`}>
              <div className="flex items-center justify-between gap-2">
                <button className="text-left font-serif text-lg hover:text-gold" onClick={() => setEditing(s)}>
                  {s.name}
                </button>
                <div className="flex items-center gap-2">
                  <Badge>{s.status}</Badge>
                  <ActivateButton campaignId={campaignId} sceneId={s.id} disabled={!session.data || session.data.scene_id === s.id} />
                </div>
              </div>
              {s.summary_public && <p className="mt-1 line-clamp-2 text-sm text-parchment-dim">{s.summary_public}</p>}
            </li>
          ))}
        </ul>
      </Panel>
      {editing && <SceneEditor key={editing.id} campaignId={campaignId} scene={editing} onDone={() => setEditing(null)} />}
    </div>
  );
}

function ActivateButton({ campaignId, sceneId, disabled }: { campaignId: string; sceneId: string; disabled: boolean }) {
  const session = useSession(campaignId);
  const mutation = useCampaignMutation<{ scene_id: string }>(campaignId, "PATCH", () => `/sessions/${session.data?.id}`);
  return (
    <Button variant="primary" disabled={disabled || mutation.isPending} onClick={() => mutation.mutate({ scene_id: sceneId })} title="La IA describirá la escena">
      Activar
    </Button>
  );
}

function SceneEditor({ campaignId, scene, onDone }: { campaignId: string; scene: Scene; onDone: () => void }) {
  const maps = useMaps(campaignId);
  const [form, setForm] = useState({
    name: scene.name,
    summary_public: scene.summary_public ?? "",
    summary_dm: scene.summary_dm ?? "",
    map_id: scene.map_id ?? "",
    lighting: scene.lighting,
  });
  const save = useCampaignMutation<typeof form>(campaignId, "PATCH", `/scenes/${scene.id}`);
  const remove = useCampaignMutation<null>(campaignId, "DELETE", `/scenes/${scene.id}`);
  return (
    <Panel title="Editar escena">
      <form
        className="flex flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          save.mutate({ ...form, map_id: form.map_id || (null as unknown as string) }, { onSuccess: onDone });
        }}
      >
        <Field label="Nombre">
          <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </Field>
        <Field label="Descripción para los jugadores (texto para leer en voz alta)">
          <TextArea rows={5} value={form.summary_public} onChange={(e) => setForm({ ...form, summary_public: e.target.value })} />
        </Field>
        <Field label="Notas del DM (secretos de la escena; la IA las usa para arbitrar, nunca las lee en voz alta)">
          <TextArea rows={5} value={form.summary_dm} onChange={(e) => setForm({ ...form, summary_dm: e.target.value })} />
        </Field>
        <div className="grid grid-cols-2 gap-3">
          <Field label="Mapa">
            <Select value={form.map_id} onChange={(e) => setForm({ ...form, map_id: e.target.value })}>
              <option value="">— sin mapa —</option>
              {maps.data?.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label="Iluminación">
            <Select value={form.lighting} onChange={(e) => setForm({ ...form, lighting: e.target.value })}>
              <option value="bright">Brillante</option>
              <option value="dim">Tenue</option>
              <option value="dark">Oscuridad</option>
            </Select>
          </Field>
        </div>
        <ErrorText error={save.error ?? remove.error} />
        <div className="flex justify-between">
          <Button type="button" variant="danger" onClick={() => window.confirm("¿Borrar la escena?") && remove.mutate(null, { onSuccess: onDone })}>
            Borrar
          </Button>
          <div className="flex gap-2">
            <Button type="button" onClick={onDone}>
              Cerrar
            </Button>
            <Button variant="primary">Guardar</Button>
          </div>
        </div>
      </form>
    </Panel>
  );
}
